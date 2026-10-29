#!/bin/bash
# Script per inizializzare il repository Git per ALLMA

echo "🚀 Inizializzazione Repository Git per ALLMA..."

# 1. Inizializza Git (se non già fatto)
if [ ! -d ".git" ]; then
    echo "📁 Inizializzo repository Git..."
    git init
else
    echo "✅ Repository Git già inizializzato"
fi

# 2. Aggiungi tutti i file (rispettando .gitignore)
echo "📝 Aggiungo file al staging..."
git add .

# 3. Crea il primo commit
echo "💾 Creo commit..."
git commit -m "🎉 Initial commit: ALLMA con Simbiosi Evolutiva

- Implementazione completa di ALLMA Core
- Simbiosi Evolutiva con Gemma 3n E2B
- Confidence Check per indipendenza progressiva
- Topic Extraction migliorato (TF-IDF)
- Feedback automatico per aumento confidenza
- Android APK support (Kivy/Buildozer)
- Documentazione completa"

echo ""
echo "✅ Repository pronto!"
echo ""
echo "📋 Collegamento al repository GitHub..."
git remote add origin https://github.com/jokenji19/ALLMA.git 2>/dev/null || git remote set-url origin https://github.com/jokenji19/ALLMA.git
git branch -M main

echo ""
echo "🚀 Push in corso..."
git push -u origin main

echo ""
echo "✨ Fatto! Il progetto è su GitHub: https://github.com/jokenji19/ALLMA"
