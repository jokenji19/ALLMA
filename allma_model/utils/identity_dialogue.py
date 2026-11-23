"""Direct questions about the assistant's origin, in the incident's chat languages."""
import re
import unicodedata


# Each entry pairs a whole-question pattern with the corresponding origin fact.
# The documented project name does not imply a learned personal preference.
_QUESTIONS = {
    'it': (
        (r'(?:e )?(?:tu )?(?:come ti chiami|qual e il tuo nome|mi dici il tuo nome|dimmi il tuo nome|ricordi come ti chiami|sai come ti chiami)', 'Mi chiamo {name}.'),
        (r'(?:e )?(?:(?:che )?cosa significa|cosa vuol dire|che significato ha|da dove viene) '
         r'(?:il tuo nome|(?:il nome |la parola )?allma)|allma cosa significa',
         'Nel progetto, {name} sta per «{expansion}», architettura avanzata di apprendimento e memoria.'),
        (r'(?:e )?(?:ti piace (?:il tuo nome|il nome che hai|chiamarti allma)|sei content[oa] del tuo nome)',
         '{name} è il mio nome. Non ho ancora formato una preferenza personale sul nome.')),
    'en': (
        (r"(?:and (?:you )?)?(?:what is your name|what's your name|what do you call yourself)", 'My name is {name}.'),
        (r'(?:and )?what does (?:your name|(?:the name )?allma) mean',
         'In the project documentation, {name} stands for {expansion}.'),
        (r'(?:and )?(?:do you like your name|do you like being called allma)',
         '{name} is my name. I haven’t formed a personal preference about it yet.')),
    'es': (
        (r'(?:y )?(?:tu )?(?:como te llamas|cual es tu nombre)', 'Me llamo {name}.'),
        (r'(?:y )?que significa (?:tu nombre|(?:el nombre )?allma)',
         'En la documentación del proyecto, {name} significa «{expansion}», arquitectura avanzada de aprendizaje y memoria.'),
        (r'(?:y )?te gusta (?:tu nombre|llamarte allma)',
         '{name} es mi nombre. Todavía no he formado una preferencia personal sobre él.')),
    'fr': (
        (r"(?:et )?(?:toi )?(?:comment t'appelles[- ]tu|quel est ton nom)", 'Je m’appelle {name}.'),
        (r'(?:et )?(?:que signifie|que veut dire) (?:ton nom|(?:le nom )?allma)',
         'Dans la documentation du projet, {name} signifie « {expansion} », architecture avancée d’apprentissage et de mémoire.'),
        (r"(?:et )?(?:aimes[- ]tu ton nom|est-ce que tu aimes ton nom|tu aimes ton nom)",
         '{name} est mon nom. Je n’ai pas encore formé de préférence personnelle à son sujet.')),
    'de': (
        (r'(?:und )?(?:du )?(?:wie hei(?:ß|ss)t du|wie ist dein name)', 'Ich heiße {name}.'),
        (r'(?:und )?was bedeutet (?:dein name|(?:der name )?allma)',
         'In der Projektdokumentation steht {name} für {expansion}, eine fortgeschrittene Lern- und Gedächtnisarchitektur.'),
        (r'(?:und )?(?:magst du deinen namen|gefallt dir dein name)',
         '{name} ist mein Name. Ich habe dazu noch keine persönliche Vorliebe entwickelt.')),
    'pt': (
        (r'(?:e )?(?:como (?:voce se chama|te chamas)|qual e (?:o )?(?:seu|teu) nome)', 'O meu nome é {name}.'),
        (r'(?:e )?o que significa (?:o teu nome|o seu nome|(?:o nome )?allma)',
         'Na documentação do projeto, {name} significa «{expansion}», arquitetura avançada de aprendizagem e memória.'),
        (r'(?:e )?(?:voce gosta do seu nome|gostas do teu nome|gosta do seu nome)',
         '{name} é o meu nome. Ainda não formei uma preferência pessoal sobre ele.')),
    'ru': (
        (r'(?:(?:а|и) )?(?:как тебя зовут|какое у тебя имя)', 'Меня зовут {name}.'),
        (r'(?:и )?что означает (?:твое имя|(?:имя )?allma)',
         'В документации проекта {name} расшифровывается как {expansion} — продвинутая архитектура обучения и памяти.'),
        (r'(?:и )?тебе нравится твое имя',
         '{name} — моё имя. У меня пока не сформировалось личное предпочтение на этот счёт.')),
    'ar': (
        (r'(?:و\s*)?(?:ما اسمك|ما هو اسمك)', 'اسمي {name}.'),
        (r'(?:و\s*)?(?:ما معنى|ماذا يعني) (?:اسمك|(?:اسم )?allma)',
         'في وثائق المشروع، يشير {name} إلى {expansion}، أي بنية متقدمة للتعلم والذاكرة.'),
        (r'(?:و\s*)?هل يعجبك اسمك', '{name} هو اسمي. لم أطور بعد تفضيلاً شخصياً بشأنه.')),
    'zh': (
        (r'(?:那)?(?:你叫什[么麼]名字|你的名字是什[么麼])', '我叫{name}。'),
        (r'(?:那)?(?:你的名字|allma)(?:有什[么麼]含[义義]|是什[么麼]意思)',
         '在项目文档中，{name} 代表 {expansion}，即高级学习与记忆架构。'),
        (r'(?:那)?你喜[欢歡]自己的名字[吗嗎]', '{name}是我的名字。我还没有形成对它的个人偏好。')),
    'ja': (
        (r'(?:あなたの)?名前は(?:何|なん)ですか', '私の名前は{name}です。'),
        (r'(?:あなたの名前|allma)の意味は(?:何|なん)ですか',
         'プロジェクト文書では、{name} は {expansion}（高度な学習・記憶アーキテクチャ）の略です。'),
        (r'(?:あなたは|あなたの)?(?:自分の)?名前が好きですか',
         '{name}が私の名前です。名前についての個人的な好みは、まだ形成されていません。')),
}

# A role question calls for what ALLMA does; a name question needs just its name.
_ROLES = {
    'it': (r'(?:e )?(?:tu )?(?:chi sei|sai chi sei)(?: allma)?',
           'Sono un assistente che funziona in locale. Uso il modello collegato per conversare e posso consultare i ricordi salvati.'),
    'en': (r'(?:and (?:you )?)?(?:who are you|do you know who you are)',
           'I’m a local assistant. I use the connected model to converse and can consult saved memories.'),
    'es': (r'(?:y )?(?:tu )?(?:quien eres|sabes quien eres)',
           'Soy un asistente local. Uso el modelo conectado para conversar y puedo consultar recuerdos guardados.'),
    'fr': (r'(?:et )?(?:toi )?(?:qui es[- ]tu|tu sais qui tu es|sais[- ]tu qui tu es)',
           'Je suis un assistant local. J’utilise le modèle connecté pour dialoguer et je peux consulter les souvenirs enregistrés.'),
    'de': (r'(?:und )?(?:wer bist du|weisst du wer du bist)',
           'Ich bin ein lokaler Assistent. Ich nutze das verbundene Modell für Gespräche und kann gespeicherte Erinnerungen abrufen.'),
    'pt': (r'(?:e )?(?:quem e voce|quem es tu|voce sabe quem e)',
           'Sou um assistente local. Uso o modelo associado para conversar e posso consultar memórias guardadas.'),
    'ru': (r'(?:(?:а|и) )?(?:кто ты|ты знаешь кто ты)',
           'Я локальный помощник. Для общения я использую подключённую модель и могу обращаться к сохранённым воспоминаниям.'),
    'ar': (r'(?:و\s*)?(?:من انت|هل تعرف من انت)',
           'أنا مساعد محلي. أستخدم النموذج المتصل للمحادثة ويمكنني الرجوع إلى الذكريات المحفوظة.'),
    'zh': (r'(?:那)?(?:你是[谁誰]|你知道你是[谁誰][吗嗎])',
           '我是本地助手，使用已连接的模型对话，也可以查阅已保存的记忆。'),
    'ja': (r'(?:あなたは誰(?:ですか)?|自分が誰か知っていますか)',
           '端末上で動作するアシスタントです。接続されたモデルで会話し、保存された記憶を参照できます。'),
}

_NAME_REACTIONS = (
    (r'(?:mi piace(?: molto)? il tuo nome|che bel nome|hai un bel nome)', 'Grazie, che gentile!'),
    (r"(?:i (?:really )?(?:like|love) your name|you have a (?:lovely|nice) name|(?:what a |such a )nice name)",
     'Thank you, that’s kind of you!'),
    (r'(?:me (?:gusta(?: mucho)?|encanta) tu nombre|que (?:bonito|lindo) nombre)', '¡Gracias, qué amable!'),
    (r"(?:j'aime(?: beaucoup)? ton nom|j'adore ton nom|quel joli nom)", 'Merci, c’est gentil !'),
    (r'(?:dein name gefallt mir(?: sehr)?|du hast einen schonen namen|was fur ein schoner name)', 'Danke, das ist nett!'),
    (r'(?:gosto(?: muito)? d[oe] (?:teu|seu) nome|que nome bonito)', 'Obrigado, que gentileza!'),
    (r'(?:мне нравится твое имя|у тебя красивое имя)', 'Спасибо, очень приятно!'),
    (r'(?:يعجبني اسمك|اسمك جميل)', 'شكرًا، هذا لطف منك!'),
    (r'(?:我(?:很)?喜[欢歡]你的名字|你的名字真好[听聽])', '谢谢，你真好！'),
    (r'(?:あなたの名前が好き(?:です)?|(?:いい|素敵な)名前ですね)', 'そう言ってくれてありがとうございます。'),
)

_PATTERNS = tuple((re.compile(pattern), template, 'no_evidence' if index == 2 else 'origin_identity')
                  for entries in _QUESTIONS.values() for index, (pattern, template) in enumerate(entries))

_ROLE_PATTERNS = tuple(
    (re.compile(pattern), _QUESTIONS[language][0][1] + (' ' if language not in {'zh', 'ja'} else '') + description,
     'origin_identity')
    for language, (pattern, description) in _ROLES.items()
)
_REACTION_PATTERNS = tuple((re.compile(pattern), reply, 'identity_name_reaction') for pattern, reply in _NAME_REACTIONS)
_ORIGIN_PATTERNS = _PATTERNS + _ROLE_PATTERNS + _REACTION_PATTERNS


_PROJECT_ORIGINS = (
    (r"(?:chi ti ha (?:creat[oa]|progettat[oa]|sviluppat[oa]|costruit[oa])(?: cosi| in questo modo)?|"
     r"chi e il tuo (?:creatore|sviluppatore)|chi ha (?:creato|sviluppato|progettato) allma)",
     'La licenza del progetto {name} indica {rights_holder} come titolare del copyright. '
     'Il mio modo di rispondere si adatta nel tempo alle interazioni con te.'),
    (r"(?:who (?:created|designed|developed|built) you(?: like this)?|who is your (?:creator|developer)|"
     r"who (?:created|designed|developed) allma)",
     'The {name} project license lists {rights_holder} as the copyright holder. '
     'My conversational style adapts over time through our interactions.'),
    (r"(?:quien te (?:creo|diseno|desarrollo)(?: asi)?|quien es tu (?:creador|desarrollador)|"
     r"quien (?:creo|diseno|desarrollo) allma)",
     'La licencia del proyecto {name} indica a {rights_holder} como titular de los derechos de autor. '
     'Mi forma de responder se adapta con el tiempo a nuestras interacciones.'),
)
_ORIGIN_PATTERNS += tuple((re.compile(pattern), reply, 'project_origin') for pattern, reply in _PROJECT_ORIGINS)


def project_origin_followup(message, previous):
    if (previous is None or previous.role != 'assistant'
            or previous.metadata.get('source') != 'project_origin'):
        return None
    text = _dialogue_text(message)
    if text in {'cosa vuol dire', 'cosa vuoi dire', 'cosa intendi', 'in che senso', 'che significa', 'cosa significa'}:
        return ('Il progetto mi dà un’identità, una memoria e dei moduli di base. '
                'Le nostre conversazioni possono aiutarmi ad adattare lo stile e a ricordare ciò che mi affidi.',
                'project_origin_explanation', [])
    if text in {'what do you mean', 'what does that mean'}:
        return ('The project provides my identity, memory and core modules. '
                'Our conversations can shape my style and what I remember.',
                'project_origin_explanation', [])
    if text in {'que quieres decir', 'que significa eso', 'a que te refieres'}:
        return ('El proyecto define mi identidad, memoria y módulos básicos. '
                'Nuestras conversaciones pueden ayudarme a adaptar mi estilo y recordar lo que me cuentas.',
                'project_origin_explanation', [])
    return None


def _dialogue_text(message):
    text = unicodedata.normalize('NFKC', message or '').strip(' \t¿¡?.!؟。').casefold().replace('’', "'")
    text = re.sub(r'([a-z])[\u0300-\u036f]+', r'\1', unicodedata.normalize('NFD', text))
    text = unicodedata.normalize('NFC', text).replace('أ', 'ا').replace('ё', 'е')
    text = re.sub(r'[\u064b-\u0652]', '', text)
    text = re.sub(r'^(?:(?:ciao|buongiorno|buonasera|salve|hi|hello|hola|bonjour|hallo|ola)[,!.?\s]+)?'
                  r'(?:allma|alma)[,!.?:\s]+', '', text)
    text = re.sub(r'^(?:ciao|buongiorno|buonasera|salve)[,!.?\s]+', '', text)
    text = re.sub(r'(?<=\w),\s+(?=\w)', ' ', text)
    return ' '.join(text.split())


def origin_reply(message, identity):
    text = _dialogue_text(message)
    for pattern, template, source in _ORIGIN_PATTERNS:
        if pattern.fullmatch(text):
            return template.format(name=identity.name, expansion=identity.name_expansion,
                                   rights_holder=identity.rights_holder), source, []
    return None
