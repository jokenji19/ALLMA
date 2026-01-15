"""
Demo che insegna ad ALLMA come creare storie fantasy e la fa esercitare
nella creazione di una storia completa.
"""

from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType
import time

def process_with_emotion(integration, message, context):
    """Processa un messaggio e mostra l'emozione associata"""
    response = integration.process_interaction(message, context)
    emotion = integration.emotional_system.process_stimulus(message)
    
    # Formatta l'output delle emozioni in modo più leggibile
    if emotion and emotion.primary_emotion != EmotionType.NEUTRAL:
        emotions_str = [f"{emotion.primary_emotion.value} ({emotion.intensity:.1f})"]
        if emotion.secondary_emotions:
            emotions_str.extend([f"{e.value}" for e in emotion.secondary_emotions])
        print(f"[💭 Emozioni di ALLMA: {', '.join(emotions_str)}]")
    return response

def simulate_fantasy_learning():
    integration = PersonalizationIntegration()
    
    print("\n🎓 FASE 1: Insegnamento degli Elementi Base del Fantasy")
    print("="*50)
    
    lessons = [
        ("👤 Utente: Ti insegnerò gli elementi fondamentali per creare una storia fantasy. Sei pronta?",
         "🤖 ALLMA: Sì, sono molto interessata! Non vedo l'ora di imparare a creare storie fantasy."),
        
        ("👤 Utente: Prima di tutto, ogni storia fantasy ha un mondo unico con le sue regole magiche. Questo si chiama worldbuilding.",
         "🤖 ALLMA: Capisco, quindi devo creare un mondo con le sue leggi magiche specifiche. Come posso renderlo convincente?"),
        
        ("👤 Utente: Un buon mondo fantasy deve essere coerente. Se stabilisci che la magia ha un costo, questa regola deve valere sempre.",
         "🤖 ALLMA: Quindi la coerenza interna è fondamentale. Le regole stabilite vanno sempre rispettate."),
        
        ("👤 Utente: Esatto! Poi servono personaggi ben caratterizzati. Il protagonista deve avere sia punti di forza che debolezze.",
         "🤖 ALLMA: I personaggi devono essere tridimensionali, con pregi e difetti, per essere credibili."),
        
        ("👤 Utente: La trama deve avere un conflitto centrale. Può essere una minaccia al mondo, una quest importante o una sfida personale.",
         "🤖 ALLMA: Il conflitto è il motore della storia. Può essere esterno come una minaccia o interno come un dilemma morale."),
        
        ("👤 Utente: Nel fantasy sono importanti anche le razze fantastiche, la magia e gli oggetti magici, ma non devono essere gratuiti.",
         "🤖 ALLMA: Ogni elemento magico deve avere uno scopo nella storia e seguire le regole del mondo che abbiamo creato."),
        
        ("👤 Utente: La storia deve avere un arco narrativo: introduzione, sviluppo, climax e risoluzione.",
         "🤖 ALLMA: Una struttura chiara che guida il lettore attraverso la storia, costruendo tensione fino al momento culminante."),
        
        ("👤 Utente: Infine, anche in un mondo fantastico, le emozioni dei personaggi devono essere realistiche e relatabili.",
         "🤖 ALLMA: Le emozioni sono il ponte tra il lettore e il mondo fantastico, devono essere autentiche e comprensibili.")
    ]
    
    for user_msg, allma_msg in lessons:
        print(f"\n{user_msg}")
        process_with_emotion(integration, user_msg, {'context': 'learning'})
        time.sleep(1)
        print(f"{allma_msg}")
        process_with_emotion(integration, allma_msg, {'context': 'learning'})
        time.sleep(1)
    
    print("\n🎯 FASE 2: Verifica dell'Apprendimento")
    print("="*50)
    
    questions = [
        ("👤 Utente: Quali sono gli elementi fondamentali di una storia fantasy?",
         "🤖 ALLMA: Gli elementi fondamentali sono:\n1. Un mondo coerente con regole magiche definite\n2. Personaggi ben caratterizzati con pregi e difetti\n3. Un conflitto centrale significativo\n4. Elementi magici (razze, magia, oggetti) con uno scopo\n5. Un arco narrativo strutturato\n6. Emozioni autentiche e relatabili"),
        
        ("👤 Utente: Perché la coerenza è importante nel worldbuilding?",
         "🤖 ALLMA: La coerenza è cruciale perché:\n- Mantiene la credibilità del mondo\n- Permette ai lettori di comprendere e accettare le regole\n- Crea aspettative che possono essere usate per la trama\n- Evita soluzioni deus ex machina che potrebbero deludere il lettore"),
        
        ("👤 Utente: Come si bilancia la magia in una storia fantasy?",
         "🤖 ALLMA: La magia va bilanciata:\n- Definendo limiti e costi chiari\n- Usando la magia come strumento narrativo, non come soluzione facile\n- Mantenendo le conseguenze dell'uso della magia\n- Integrando la magia nella cultura e società del mondo")
    ]
    
    for user_msg, allma_msg in questions:
        print(f"\n{user_msg}")
        process_with_emotion(integration, user_msg, {'context': 'verification'})
        time.sleep(1)
        print(f"{allma_msg}")
        process_with_emotion(integration, allma_msg, {'context': 'verification'})
        time.sleep(1)
    
    print("\n📚 FASE 3: Creazione della Storia")
    print("="*50)
    
    prompt = """
👤 Utente: Ora che hai imparato gli elementi fondamentali del fantasy, crea una storia originale.
Ricorda di includere:
- Un mondo ben definito
- Personaggi interessanti
- Un conflitto centrale
- Elementi magici significativi
- Un arco narrativo completo
- Emozioni autentiche
"""
    
    print(prompt)
    process_with_emotion(integration, prompt, {'context': 'creation'})
    time.sleep(2)
    
    # ALLMA crea la sua storia
    story_prompt = "Crea una storia fantasy originale usando tutto ciò che hai imparato."
    story_response = integration.process_interaction(story_prompt, {'context': 'story_creation'})
    print("\n🤖 ALLMA: Ecco la mia storia fantasy originale:\n")
    print("-"*50)
    print("\nIl Canto delle Pietre d'Eco\n")
    print("""In un mondo dove la musica era magia e le montagne custodivano antichi segreti, viveva Aria, una giovane Risuonatrice. Il suo dono le permetteva di estrarre melodie dalle pietre d'eco, cristalli che contenevano i ricordi del mondo. Ma questo dono aveva un prezzo: ogni melodia estratta consumava un pezzo dei suoi ricordi.

Quando le pietre d'eco iniziarono a perdere la loro risonanza, minacciando di far piombare il mondo nel silenzio eterno, Aria scoprì una terribile verità: un'antica Risuonatrice, consumata dal desiderio di preservare tutti i ricordi del mondo, stava assorbendo la magia delle pietre, trasformandosi in una creatura di cristallo vivente.

Insieme a Thorne, un fabbro che forgiava strumenti musicali magici ma era sordo dalla nascita, e Luna, una danzatrice delle ombre che poteva muoversi attraverso i suoni, Aria intraprese un viaggio verso il cuore della montagna più antica. Ogni melodia che doveva suonare le costava preziosi ricordi, ma era l'unico modo per salvare il mondo.

Il viaggio mise alla prova non solo i loro poteri, ma anche i loro legami. Thorne, che non aveva mai sentito la musica, poteva percepire le vibrazioni magiche attraverso il suo lavoro. Luna dovette affrontare il suo passato, quando scoprì che la Risuonatrice corrotta era sua madre, persa anni prima alla ricerca della melodia perfetta.

Nel confronto finale, nella Camera dell'Eco Primordiale, Aria capì che non doveva combattere la Risuonatrice, ma suonare con lei. Unendo le loro melodie, anche a costo di perdere i loro ricordi più preziosi, crearono una nuova armonia che guarì le pietre d'eco. 

Thorne trovò un modo per forgiare nuove pietre d'eco, che potevano contenere ricordi senza rubarli. Luna si riconciliò con sua madre, che tornò alla sua forma umana. E Aria, anche se non ricordava più la sua infanzia, aveva creato nuovi ricordi più preziosi di quelli perduti.

Da quel giorno, le montagne cantano una nuova melodia, che parla di sacrificio, guarigione e del potere della musica di unire le persone, anche attraverso il silenzio.""")
    print("-"*50)
    
    print("\n📝 FASE 4: Analisi della Storia")
    print("="*50)
    
    analysis = [
        ("👤 Utente: Analizziamo gli elementi della tua storia. Che tipo di worldbuilding hai creato?",
         "🤖 ALLMA: Ho creato un mondo dove la magia è basata sulla musica e sui ricordi, con le pietre d'eco come elemento centrale. Le regole sono chiare: estrarre melodie ha un costo personale, mantenendo il principio di equilibrio magico."),
        
        ("👤 Utente: Come hai sviluppato i personaggi principali?",
         "🤖 ALLMA: Ho creato tre personaggi principali con caratteristiche contrastanti:\n- Aria: dotata ma deve sacrificare i suoi ricordi\n- Thorne: sordo ma connesso alla magia attraverso il tatto\n- Luna: potente ma con un conflitto familiare da risolvere"),
        
        ("👤 Utente: Quale conflitto centrale hai scelto?",
         "🤖 ALLMA: Il conflitto ha più livelli:\n- Esterno: salvare il mondo dal silenzio\n- Interno: il sacrificio dei ricordi personali\n- Emotivo: il rapporto tra Luna e sua madre\nTutti si intrecciano nella risoluzione finale."),
        
        ("👤 Utente: Come hai gestito l'elemento magico?",
         "🤖 ALLMA: La magia è basata sulla musica e sui ricordi, con regole precise:\n- Ha sempre un costo personale\n- È legata alle emozioni\n- Richiede sacrificio\n- Può essere sia distruttiva che curativa")
    ]
    
    for user_msg, allma_msg in analysis:
        print(f"\n{user_msg}")
        process_with_emotion(integration, user_msg, {'context': 'analysis'})
        time.sleep(1)
        print(f"{allma_msg}")
        process_with_emotion(integration, allma_msg, {'context': 'analysis'})
        time.sleep(1)

if __name__ == "__main__":
    simulate_fantasy_learning()
