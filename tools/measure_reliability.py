"""CLI entry point for the shared Mac/Android operational battery."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reliability_battery import main

if __name__ == '__main__':
    main()
