# Verifiche emotive riproducibili

## Perché tre test della 0.9.1 fallivano su GitHub

La verifica Linux del commit `d16032f` riportava 2.071 casi superati, 3 falliti e 15 saltati. I tre test coinvolgevano `ContextUnderstandingSystem` e il vecchio `NLPProcessor`: si aspettavano classificazioni del modello `j-hartmann/emotion-english-distilroberta-base`, disponibile nella cache del Mac ma assente nel runner GitHub offline.

I controlli del collegamento fra componenti ora usano un classificatore controllato: verificano l'inoltro del testo, l'elaborazione dei punteggi, l'emozione trasmessa alla conversazione e le risposte contestuali. Le aspettative originali su gioia e tristezza restano presenti. Questi controlli non misurano la qualità del modello.

`tools/run_tests.py` assegna a ogni esecuzione una nuova cache Hugging Face isolata e disabilita rete e download. Anche una macchina con modelli già scaricati percorre quindi lo stesso caso di assenza del modello del runner GitHub.

## Suite offline

```sh
python3 tools/run_tests.py --batch-size 48 --timeout 240 --output test-results
```

Sono inclusi controlli aggiuntivi su caricamento fallito, inferenza fallita, input invalido, negazioni, emozioni miste e distinzione fra utente e altre persone. Gli ultimi tre attraversano `ALLMACore(mobile_mode=True)` con un generatore di risposte controllato e verificano che nessun classificatore Transformers venga caricato.

Il vecchio contesto restituisce `unknown` con punteggio zero quando manca il modello. Il vecchio NLP mantiene il segnaposto compatibile `neutral`: non è una misura attendibile dell'emozione dell'utente. Il percorso emotivo corrente di Android usa invece `EmotionalCore` e le evidenze locali; non dipende da quel modello desktop.

Le prove in modalità mobile eseguite sul computer verificano il percorso software, non costituiscono un nuovo collaudo fisico Android. Questa correzione modifica solo test, strumenti di verifica e documentazione: l'APK 0.9.1 e il suo tag rimangono invariati.

## Integrazione con il modello reale

La suite separata `tests/model_integration/` usa la revisione immutabile `0e1cd914e3d46199ed785853e12b57304e04178b`. Modello, revisione e file necessari sono dichiarati in `emotion_model.json`.

Preparazione esplicita, con rete consentita:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from huggingface_hub import snapshot_download
spec = json.loads(Path('tests/model_integration/emotion_model.json').read_text())
snapshot_download(repo_id=spec['repo_id'], revision=spec['revision'], allow_patterns=spec['files'])
PY
```

Inferenza successiva offline:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python3 -m pytest tests/model_integration --run-model-integration \
  -q --no-cov -o addopts= --junitxml=model-test-results.xml
```

Una richiesta esplicita della suite senza i pesi produce un errore: non diventa silenziosamente un successo o un test saltato. Senza `--run-model-integration`, le prove del modello restano esplicitamente disabilitate. Il workflow GitHub prepara la revisione esatta in un job separato, esegue l'inferenza offline e conserva il report. La compilazione automatica richiede il successo di entrambe le suite.

### Limite del modello osservato

La frase neutra `The weather is cloudy today.` viene classificata come tristezza dal modello fissato. Il vecchio test controllava solo la presenza di un'etichetta e non rilevava questo errore semantico. Il nuovo caso mantiene l'aspettativa `neutral` ed è dichiarato `xfail(strict=True)`: un limite noto e visibile del modello, non una prova superata. Se il comportamento cambia e la classificazione diventa corretta, il successo inatteso richiede di aggiornare questa dichiarazione.

Gli altri casi reali verificano gioia e tristezza in inglese e le due aspettative italiane originarie attraverso l'adattatore NLP, che applica anche un rinforzo lessicale. Queste ultime non dimostrano accuratezza generale del modello inglese in italiano e non misurano il riconoscimento emotivo dell'app Android.

## Risultati locali del 21 ottobre 2026

- Suite completa con cache vuota: **2.104 casi raccolti, 2.089 superati, 15 saltati, nessun fallimento**.
- Sottoinsieme mirato dei componenti modificati e dei nuovi controlli: **33 casi superati**.
- Modello reale fissato: **4 casi superati e 1 fallimento atteso**, relativo al meteo e descritto sopra.
- Controlli JavaScript previsti dal workflow: superati.

Le 15 prove saltate preesistevano a questa correzione. I 15 nuovi casi offline aggiungono copertura della disponibilità del modello e dell'isolamento dell'ambiente: i numeri non rappresentano un aumento percentuale dell'intelligenza di ALLMA.

## Primo avvio della compilazione su GitHub

Superati i test, il job di compilazione ha esposto un problema distinto: `build_android_safe.py` chiedeva sempre una pulizia alla prima esecuzione, quando il checkout di python-for-android non esiste ancora. Buildozer usa quel percorso come cartella di lavoro e terminava con `FileNotFoundError` prima di prepararlo.

La pulizia ora richiede anche che il checkout configurato esista; al primo avvio parte direttamente la preparazione della build. La verifica dell'APK resta obbligatoria e le build già inizializzate continuano a essere pulite quando cambiano gli input. Sei nuove prove sintetiche coprono avvio iniziale, cartelle personalizzate e riuso delle build. Non sostituiscono una compilazione Android completa.
