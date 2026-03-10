# ALLMA - Advanced Learning and Memory Architecture

<div align="center">

**An AI with Long-Term Memory, Emotional Intelligence, and Evolutionary Learning**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Android](https://img.shields.io/badge/Platform-Android-green.svg)](https://www.android.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## Overview

ALLMA is an advanced artificial intelligence system designed for local, offline execution, specifically optimized for mobile environments (Android). It transcends standard conversational models by integrating persistent memory, emotional awareness, and a unique self-evolving architecture.

The core philosophy of ALLMA is **Evolutionary Symbiosis**:
- **Long-Term Memory**: Retains knowledge from all past interactions using a SQLite-backed Vector Memory Engine.
- **Emotional System**: Recognizes user emotions and adapts its own internal psychological state (Chaos/Stability vectors) to provide empathetic and context-aware responses.
- **Incremental Learning**: Extracts topics and semantic networks in real-time, building a permanent internal knowledge base.
- **Symbiotic Independence**: Progressively transitions from relying entirely on the underlying Large Language Model (LLM) to answering autonomously based on its consolidated high-confidence memory.

### The Symbiotic Process with Qwen 2.5 Coder 3B / Qwen 3 1.7B

ALLMA currently utilizes the Qwen model architecture (specifically optimized versions like Qwen 2.5 Coder 3B or the lightweight Qwen 3 1.7B) as its initial linguistic reasoning engine.

1. **Initial Phase (Symbiosis)**: ALLMA relies on Qwen to process complex queries. It injects its current emotional state, relevant past memories, and system directives into a highly optimized ChatML prompt.
2. **Evolutionary Phase (Independence)**: Before querying the LLM, ALLMA scans its internal knowledge base. If an answer exists with high confidence, it can respond directly or drastically reduce the LLM workload.
3. **Advanced Phase (Autonomy)**: Continuous successful interactions automatically increase the confidence of stored knowledge, making ALLMA progressively faster and more autonomous over time.

## Key Features

- **Temporal Memory**: Recalls past conversations, understanding the temporal context of interactions.
- **Emotional Analysis**: Actively detects textual sentiment and adjusts its response trajectory based on its continuous "Soul" state.
- **Topic Extraction**: Automatically identifies and categorizes key concepts using TF-IDF and NLP techniques.
- **Confidence Check Engine**: Bypasses costly LLM generation when internal knowledge is sufficient.
- **Android Native Deployment**: Fully ported to mobile using Kivy and Buildozer, running 100% offline on the device.

## Mobile Operating System Survival Architecture (V7)

ALLMA is engineered to survive and thrive within the strict resource constraints of the Android operating system:

1. **Subconscious Daemon (Foreground Service)**: Utilizes Android Intent and `jnius` to run a persistent background service. This prevents the OS from killing the memory-building processes during Doze Mode or when the screen is off.
2. **Adaptive Metabolic Coupling**: Features a dynamic CPU/Thermal pacing system. It monitors battery temperature and automatically throttles token generation (Micro-sleep injects) to prevent device overheating and thermal shutdown.
3. **SQLite Concurrency (WAL Mode)**: The Vector Memory Engine is configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) to allow simultaneous read/write operations between the UI and background reasoning threads without database locks.
4. **LLM Fast-Wake (mmap)**: Leverages memory-mapped files (`mmap=True` via `llama-cpp-python`) to bypass RAM cold-starts, allowing the OS to page the model directly from storage for instantaneous wake-ups.

## Android APK Build Guide

The project includes the necessary configurations to build an optimized Android application.

### Prerequisites

- Python 3.10+
- Buildozer
- Android SDK/NDK (managed by Buildozer)
- Qwen 3 1.7B GGUF Model (Quantized Q4_K_M or similar, approx. 1-2GB)

### Build Steps

1. **Download the Language Model**:
   Ensure the GGUF model is placed in the designated `models/` directory.
   ```bash
   python3 download_model.py
   ```

2. **Compile the APK**:
   ```bash
   buildozer android debug
   ```

3. **Deploy to Device**:
   ```bash
   buildozer android debug deploy run
   ```

For detailed mobile deployment instructions, please consult [README_ANDROID.md](README_ANDROID.md).

## Desktop Installation

To run ALLMA in a desktop environment for development or testing:

```bash
pip install -r requirements.txt
python3 main.py
```

## System Architecture

```text
ALLMA/
├── allma_model/
│   ├── core/                  # Core runtime, Event Bus, Cognitive Pipeline
│   ├── emotional_system/      # Emotional state management and adaptation
│   ├── learning_system/       # Meta-learning and topic extraction
│   └── memory_system/         # Vector Memory Engine, Temporal Memory
├── ui/                        # Kivy Interface components
├── assets/                    # Webviews, CSS, JavaScript
└── service.py                 # Android Foreground Subconscious Daemon
```

### Source of Truth
The primary source code is located in `allma_model/`.

### Core Runtime
The application's main processing loop is managed by `allma_model/core/allma_core.py`.

## Documentation

Comprehensive documentation covering system architecture, module interactions, and implementation details:

- [SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md) - Complete system overview
- [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) - In-depth technical architecture
- [README_ANDROID.md](README_ANDROID.md) - Android specific guidelines
- [docs/](docs/) - Implementation guides and references

## Testing Framework

ALLMA includes a robust test suite covering memory, emotional logic, and evolutionary systems:

```bash
# Test Evolutionary Symbiosis
python3 test_evolution.py

# Test Automatic Confidence Boosting
python3 test_confidence_boost.py

# Run Full Pytest Suite
python3 -m pytest -q
```

## Contributing

Contributions are welcome to enhance ALLMA's cognitive capabilities.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingCognitiveFeature`)
3. Commit your Changes (`git commit -m 'Add AmazingCognitiveFeature'`)
4. Push to the Branch (`git push origin feature/AmazingCognitiveFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

## Acknowledgments

- **Qwen (Alibaba Cloud)** - For the highly capable lightweight LLM foundations
- **Kivy Framework** - For enabling python-based mobile UI deployments
- **llama.cpp** - For providing the highly optimized C++ inference engine for GGUF models
