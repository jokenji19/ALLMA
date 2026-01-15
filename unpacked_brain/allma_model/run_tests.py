import sys
import os
from typing import List, Set
from enum import Enum

class ModuleType(Enum):
    MEMORY = "memory"
    EMOTION = "emotion"
    LEARNING = "learning"
    NLP = "nlp"
    REASONING = "reasoning"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"

class TestRunner:
    def __init__(self):
        self.dependencies = {
            ModuleType.MEMORY: {ModuleType.EMOTION},
            ModuleType.EMOTION: {ModuleType.MEMORY},
            ModuleType.LEARNING: {ModuleType.MEMORY, ModuleType.NLP},
            ModuleType.NLP: {ModuleType.REASONING},
            ModuleType.REASONING: {ModuleType.NLP},
            ModuleType.INTEGRATION: {ModuleType.MEMORY, ModuleType.EMOTION, ModuleType.NLP, ModuleType.REASONING},
            ModuleType.PERFORMANCE: set()
        }
        
        self.test_files = {
            ModuleType.MEMORY: "tests/test_advanced_memory.py",
            ModuleType.EMOTION: "beta_test_twenty_years_integrated.py",
            ModuleType.LEARNING: "demo_learning_napoleon.py",
            ModuleType.NLP: "tests/test_nlp_understanding.py",
            ModuleType.REASONING: "tests/test_reasoning_response.py",
            ModuleType.INTEGRATION: "tests/test_integration.py",
            ModuleType.PERFORMANCE: "tests/test_performance.py"
        }
    
    def get_required_tests(self, modified_modules: List[ModuleType]) -> Set[ModuleType]:
        """Determina quali test devono essere eseguiti in base ai moduli modificati"""
        required_tests = set(modified_modules)
        
        # Aggiungi i test per i moduli dipendenti
        for module in modified_modules:
            for dep_module, dependencies in self.dependencies.items():
                if module in dependencies:
                    required_tests.add(dep_module)
        
        return required_tests
    
    def run_tests(self, modules_to_test: Set[ModuleType]):
        """Esegue i test per i moduli specificati"""
        print("\n=== Esecuzione Test ALLMA ===\n")
        
        for module in modules_to_test:
            test_file = self.test_files[module]
            if os.path.exists(test_file):
                print(f"\nEsecuzione test per {module.value}...")
                os.system(f"python {test_file}")
            else:
                print(f"\n⚠️ File di test mancante per {module.value}: {test_file}")
        
        print("\n=== Test Completati ===\n")

def main():
    runner = TestRunner()
    
    if len(sys.argv) < 2:
        print("Uso: python run_tests.py <modulo1> <modulo2> ...")
        print("Moduli disponibili:", [m.value for m in ModuleType])
        return
    
    # Converti gli argomenti in ModuleType
    try:
        modified_modules = [ModuleType(arg) for arg in sys.argv[1:]]
    except ValueError as e:
        print(f"Errore: modulo non valido. {e}")
        return
    
    # Determina e esegui i test necessari
    required_tests = runner.get_required_tests(modified_modules)
    
    print("\nModuli modificati:", [m.value for m in modified_modules])
    print("Test da eseguire:", [m.value for m in required_tests])
    
    confirm = input("\nProcedere con l'esecuzione dei test? [y/N] ")
    if confirm.lower() == 'y':
        runner.run_tests(required_tests)

if __name__ == "__main__":
    main()
