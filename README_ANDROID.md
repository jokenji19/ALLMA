# Guida alla Compilazione Android (APK)

Questa guida spiega come compilare il progetto ALLMA in un file `.apk` installabile su Android.

## Prerequisiti

### Su macOS / Linux
Assicurati di avere installato:
- Python 3
- Git
- Cython (`pip install cython`)
- Buildozer (`pip install buildozer`)

### Su Windows
Buildozer non supporta nativamente Windows. Si consiglia di utilizzare:
- **WSL (Windows Subsystem for Linux)**
- Una macchina virtuale Linux (Ubuntu)
- **Google Colab** (metodo più semplice, vedi sotto)

## Istruzioni di Compilazione

1.  **Apri il terminale** nella cartella del progetto:
    ```bash
    cd /path/to/ALLMA/MODELLO_SVILUPPO_ALLMA(versione 4 stabile)
    ```

2.  **Inizializza Buildozer** (già fatto, il file `buildozer.spec` è presente):
    ```bash
    buildozer init
    ```

3.  **Aggiorna il blob del core**:
    ```bash
    python3 pack_brain.py
    ```

4.  **Oppure usa la build sicura automatica**:
    ```bash
    python3 tools/build_android_safe.py
    ```

5.  **Lancia la compilazione**:
    ```bash
    buildozer android debug
    ```
    *La prima volta questo processo può richiedere 15-30 minuti perché deve scaricare l'Android SDK/NDK.*

6.  **Trova l'APK**:
    Al termine, troverai il file `.apk` nella cartella `bin/`.

7.  **Installa su dispositivo**:
    Collega il telefono via USB (con Debug USB attivo) e esegui:
    ```bash
    buildozer android deploy run
    ```

## Compilazione con Google Colab (Consigliato)

Se non hai un ambiente Linux pronto, puoi usare questo notebook Colab:

1.  Carica l'intera cartella del progetto su Google Drive.
2.  Crea un nuovo notebook Colab.
3.  Esegui questi comandi in una cella:

```python
!pip install buildozer cython
!sudo apt-get install -y \
    python3-pip \
    build-essential \
    git \
    python3 \
    python3-dev \
    ffmpeg \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libswscale-dev \
    libavformat-dev \
    libavcodec-dev \
    zlib1g-dev

# Spostati nella cartella del progetto (modifica il percorso)
%cd /content/drive/MyDrive/ALLMA/MODELLO_SVILUPPO_ALLMA(versione 4 stabile)

# Pulisci build precedenti
!buildozer android clean

# Compila
!buildozer android debug
```

## Gestione Modello LLM (Intelligenza Artificiale)

> [!IMPORTANT]
> Il file `model-00002-of-00004.safetensors` che hai scaricato fa parte di un modello molto grande (>20GB). **Non è possibile usarlo direttamente su un cellulare** perché richiede troppa memoria RAM.

Per far funzionare l'IA sul telefono, devi usare una versione **"Quantizzata"** (compressa) del modello.

### Come fare:
1.  **Download Automatico**: Esegui lo script incluso nel progetto:
    ```bash
    python3 download_model.py
    ```
    Questo scaricherà automaticamente **Gemma 3n E2B** (versione ottimizzata) nella cartella `assets/`.

2.  **Compilazione**:
    ```bash
    buildozer android debug
    ```

### Simbiosi ALLMA-Gemma
Il sistema è configurato per una **simbiosi totale**:
- **ALLMA** gestisce la memoria a lungo termine, le emozioni e la personalità.
- **Gemma 3n E2B** agisce come il centro del linguaggio, generando le frasi.
- Prima di ogni risposta, ALLMA "inietta" il suo stato emotivo e i ricordi rilevanti nel cervello di Gemma, garantendo che l'IA parli come un'unica entità coerente.

## Note Importanti

- **Modello AI**: L'app è configurata in `mobile_mode`. Questo significa che userà modelli ottimizzati e non caricherà librerie pesanti come `transformers` completo se non strettamente necessario.
- **Permessi**: L'app richiederà permessi di lettura/scrittura memoria per salvare il database di apprendimento (`allma.db`).
