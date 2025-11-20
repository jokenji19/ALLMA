#!/bin/bash
# Script per eseguire test coverage e generare report

echo "🧪 Esecuzione Test Coverage per ALLMA..."

# Installa dipendenze se necessario
pip install -q pytest pytest-cov 2>/dev/null || echo "Dependencies già installate"

# Esegui test con coverage
echo "📊 Running tests..."
pytest --cov=Model --cov-report=html --cov-report=term-missing --cov-fail-under=60 -v

# Genera summary
echo ""
echo "✅ Coverage report generato!"
echo "📄 Apri: htmlcov/index.html"
echo ""
echo "📈 Summary:"
coverage report --skip-covered

# Apri report in browser (macOS)
if command -v open &> /dev/null; then
    echo ""
    read -p "Aprire report nel browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open htmlcov/index.html
    fi
fi
