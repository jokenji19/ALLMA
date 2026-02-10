# ALLMA - Advanced Learning and Emotional Memory Architecture

<div align="center">

**Un'IA con Memoria, Emozioni e Apprendimento Evolutivo**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Android](https://img.shields.io/badge/Platform-Android-green.svg)](https://www.android.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 🧠 Cos'è ALLMA?

ALLMA è un sistema di intelligenza artificiale avanzato che combina:
- **Memoria a Lungo Termine**: Ricorda tutto ciò che apprende
- **Sistema Emotivo**: Reagisce emotivamente alle conversazioni
- **Apprendimento Incrementale**: Impara dall'utente in tempo reale
- **Simbiosi Evolutiva**: Diventa progressivamente indipendente da modelli esterni

### 🤝 La Simbiosi con Gemma 3n E2B

ALLMA utilizza un approccio unico chiamato **Simbiosi Evolutiva**:

1. **Fase Iniziale (Simbiosi)**: ALLMA usa Gemma come "cervello linguistico"
   - Inietta le proprie emozioni e ricordi nel prompt
   - Apprende dalle risposte generate

2. **Fase Evolutiva (Indipendenza)**: 
   - ALLMA controlla la propria memoria prima di chiamare Gemma
   - Se possiede conoscenza con alta confidenza → **Risponde da solo**
   - Altrimenti → Usa Gemma e impara

3. **Fase Avanzata (Autonomia)**:
   - Dopo N risposte indipendenti di successo, la confidenza aumenta automaticamente
   - ALLMA diventa sempre più veloce e autonomo

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Simbiosi   │ --> │  Evoluzione  │ --> │  Autonomia  │
│ (usa Gemma) │     │ (controllo   │     │ (indipenden-│
│             │     │  memoria)    │     │  te)        │
└─────────────┘     └──────────────┘     └─────────────┘
```

## 🚀 Features Principali

- ✅ **Memoria Temporale**: Ricorda conversazioni nel tempo
- ✅ **Analisi Emotiva**: Rileva e reagisce alle emozioni
- ✅ **Topic Extraction**: Estrae automaticamente i concetti chiave (TF-IDF)
- ✅ **Confidence Check**: Risponde autonomamente quando "sa" la risposta
- ✅ **Feedback Automatico**: La confidenza aumenta con l'uso
- ✅ **Android Ready**: Porting completo su mobile con Kivy/Buildozer

## 📱 Android APK

Il progetto include una **versione Android** completa che funziona 100% offline sul dispositivo.

### Come Buildare l'APK

1. **Download del modello**:
```bash
python3 download_model.py
```

2. **Build APK**:
```bash
buildozer android debug
```

Per istruzioni dettagliate, consulta [README_ANDROID.md](README_ANDROID.md).

## 🛠️ Requisiti

### Desktop
```bash
pip install -r requirements.txt
```

### Mobile (Android)
- Modello Gemma 3n E2B (quantizzato Q4_K_M, ~2.6GB)
- Android SDK 28+
- 4GB+ RAM

## 📊 Architettura

```
ALLMA/
├── allma_model/
│   ├── core/
│   ├── emotional_system/
│   ├── incremental_learning/
│   ├── learning_system/
│   └── response_system/
├── ui/
├── assets/
└── docs/
```

### Fonte di verità
La sorgente primaria è `allma_model/`.  
`unpacked_brain/` è un artefatto di build locale e non va usato per lo sviluppo.

### Core runtime
Il core runtime è `allma_model/core/allma_core.py`.  
`allma_model/incremental_learning/allma_core.py` è riservato a scenari legacy/training.

### Guardrail
I moduli attivi e sperimentali sono tracciati in `ALLMACore` tramite:
- `active_modules`
- `experimental_modules`

## 🎯 Esempio di Evoluzione

```python
# Conversazione 1 - Simbiosi
User: "Cos'è Python?"
ALLMA: [Chiama Gemma] → "Python è un linguaggio..." [Memorizza]

# Conversazione 2-4 - Simbiosi con Memoria
User: "Cos'è Python?"
ALLMA: [Confidenza MEDIUM, usa Gemma] → Risposta + successo registrato

# Conversazione 5+ - Indipendenza
User: "Cos'è Python?"
ALLMA: 💡 [Confidenza HIGH, memoria interna] → Risposta IMMEDIATA!
```

## 📖 Documentazione

- [SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md) - Documentazione completa del sistema
- [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) - Architettura tecnica
- [README_ANDROID.md](README_ANDROID.md) - Build Android
- [docs/](docs/) - Guide di implementazione

## 🧪 Test

```bash
# Test Simbiosi Evolutiva
python3 test_evolution.py

# Test Feedback Automatico
python3 test_confidence_boost.py

# Test Completo
python3 -m pytest -q
```

## 🤝 Contribuire

Contributi benvenuti! Per favore:
1. Fork del progetto
2. Crea un branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

## 📄 Licenza

Vedi il file [LICENSE](LICENSE) per i dettagli.

## 🙏 Riconoscimenti

- **Gemma 3n E2B** (Google) - Modello LLM per la generazione del linguaggio
- **Kivy** - Framework UI per Android
- **llama.cpp** - Inferenza efficiente dei modelli GGUF

---

<div align="center">

**Creato con ❤️ per esplorare l'evoluzione dell'intelligenza artificiale**

</div>
