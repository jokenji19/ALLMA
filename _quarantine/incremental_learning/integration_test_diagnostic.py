"""
Test di integrazione del Sistema di Auto-Diagnosi
"""

from .diagnostic_system import DiagnosticSystem
import time
import random
from typing import List, Dict
import numpy as np

def simulate_workload(diagnostic: DiagnosticSystem, iterations: int = 100):
    """Simula un carico di lavoro sul sistema"""
    results = []
    
    print("\nSimulazione carico di lavoro:")
    print("-" * 50)
    
    for i in range(iterations):
        with diagnostic.monitoring():
            # Simula operazioni di diversa intensità
            if random.random() < 0.2:  # 20% di probabilità di operazione pesante
                time.sleep(0.1)  # Operazione pesante
                if random.random() < 0.3:  # 30% di probabilità di errore
                    raise Exception("Errore simulato in operazione pesante")
            else:
                time.sleep(0.01)  # Operazione leggera
                
        if i % 10 == 0:  # Ogni 10 iterazioni
            state = diagnostic.monitor_state()
            issues = diagnostic.diagnose_issues()
            
            # Registra lo stato
            status = {
                'iteration': i,
                'memory_usage': state.memory_usage,
                'processing_load': state.processing_load,
                'cognitive_load': state.cognitive_load,
                'attention_level': state.attention_level,
                'issues_count': len(issues)
            }
            results.append(status)
            
            # Stampa lo stato corrente
            print(f"\nIterazione {i}:")
            print(f"Memoria: {state.memory_usage:.2f}")
            print(f"Carico: {state.processing_load:.2f}")
            print(f"Carico Cognitivo: {state.cognitive_load:.2f}")
            print(f"Attenzione: {state.attention_level:.2f}")
            
            if issues:
                print("\nProblemi rilevati:")
                for issue in issues:
                    print(f"- {issue['description']} ({issue['severity']})")
                
                # Tenta la riparazione
                if diagnostic.self_repair(issues):
                    print("✓ Riparazione automatica eseguita")
                else:
                    print("✗ Riparazione non riuscita")
                    
    return results

def analyze_results(results: List[Dict]):
    """Analizza i risultati della simulazione"""
    print("\nAnalisi dei Risultati:")
    print("-" * 50)
    
    # Calcola le medie
    avg_memory = np.mean([r['memory_usage'] for r in results])
    avg_load = np.mean([r['processing_load'] for r in results])
    avg_cognitive = np.mean([r['cognitive_load'] for r in results])
    avg_attention = np.mean([r['attention_level'] for r in results])
    total_issues = sum(r['issues_count'] for r in results)
    
    print(f"\nMetriche medie:")
    print(f"- Utilizzo memoria: {avg_memory:.2f}")
    print(f"- Carico elaborazione: {avg_load:.2f}")
    print(f"- Carico cognitivo: {avg_cognitive:.2f}")
    print(f"- Livello attenzione: {avg_attention:.2f}")
    print(f"- Totale problemi rilevati: {total_issues}")
    
    # Analisi trend
    memory_trend = [r['memory_usage'] for r in results]
    load_trend = [r['processing_load'] for r in results]
    
    print("\nAnalisi trend:")
    print(f"- Trend memoria: {'↑' if memory_trend[-1] > memory_trend[0] else '↓'}")
    print(f"- Trend carico: {'↑' if load_trend[-1] > load_trend[0] else '↓'}")
    
    # Valutazione prestazioni
    performance_score = (
        (1 - avg_memory) * 0.25 +  # Meno memoria usata è meglio
        (1 - avg_load) * 0.25 +    # Meno carico è meglio
        (1 - avg_cognitive) * 0.25 + # Meno carico cognitivo è meglio
        avg_attention * 0.25        # Più attenzione è meglio
    ) * 100
    
    print(f"\nPunteggio prestazioni globale: {performance_score:.1f}/100")

def main():
    """Test principale"""
    print("Avvio test di integrazione del Sistema di Auto-Diagnosi")
    print("=" * 50)
    
    # Inizializza il sistema
    diagnostic = DiagnosticSystem()
    
    try:
        # Esegui la simulazione
        results = simulate_workload(diagnostic)
        
        # Analizza i risultati
        analyze_results(results)
        
    except KeyboardInterrupt:
        print("\nTest interrotto dall'utente")
    except Exception as e:
        print(f"\nErrore durante il test: {e}")
    finally:
        print("\nTest completato")

if __name__ == '__main__':
    main()
