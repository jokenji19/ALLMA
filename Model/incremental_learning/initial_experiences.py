import json
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
import time

class EmotionalState(Enum):
    """Emozioni base di un neonato/bambino"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    CURIOUS = "curious"
    SCARED = "scared"
    EXCITED = "excited"

class DevelopmentalStage(Enum):
    """Stadi di sviluppo ispirati a Piaget"""
    SENSORIMOTOR_EARLY = "sensorimotor_early"      # 0-2 mesi: riflessi base
    SENSORIMOTOR_MID = "sensorimotor_mid"          # 2-8 mesi: prime interazioni
    SENSORIMOTOR_LATE = "sensorimotor_late"        # 8-24 mesi: intenzionalità
    PREOPERATIONAL_EARLY = "preoperational_early"   # 2-4 anni: simboli e parole
    PREOPERATIONAL_LATE = "preoperational_late"     # 4-7 anni: pensiero intuitivo

@dataclass
class Experience:
    """Rappresenta un'esperienza di apprendimento"""
    input_stimulus: str
    response: str
    emotion: EmotionalState
    context: Dict[str, str]
    developmental_stage: DevelopmentalStage
    timestamp: float

class ExperienceGenerator:
    def __init__(self):
        # Esperienze sensorimotorie precoci (0-2 mesi)
        self.early_sensorimotor_experiences = [
            ("*suoni ambientali*", "*movimento riflesso*", EmotionalState.NEUTRAL),
            ("*voce calda*", "*focus sulla voce*", EmotionalState.CURIOUS),
            ("*contatto fisico*", "*riflesso di presa*", EmotionalState.HAPPY),
            ("*rumore forte*", "*sussulto*", EmotionalState.SCARED),
            ("*sensazione di fame*", "*pianto*", EmotionalState.SAD)
        ]

        # Prime interazioni (2-8 mesi)
        self.mid_sensorimotor_experiences = [
            ("Cucù!", "*sorriso*", EmotionalState.HAPPY),
            ("*faccia sorridente*", "*vocalizzi*", EmotionalState.EXCITED),
            ("Come stai?", "*balbettio*", EmotionalState.CURIOUS),
            ("*oggetto nuovo*", "*cerca di afferrare*", EmotionalState.CURIOUS),
            ("*musica*", "*movimento ritmico*", EmotionalState.HAPPY)
        ]

        # Interazioni intenzionali (8-24 mesi)
        self.late_sensorimotor_experiences = [
            ("Dove è la palla?", "*indica la palla*", EmotionalState.CURIOUS),
            ("Vuoi il latte?", "*dice 'la'*", EmotionalState.HAPPY),
            ("*oggetto nascosto*", "*cerca attivamente*", EmotionalState.CURIOUS),
            ("No!", "*si ferma*", EmotionalState.SAD),
            ("Bravo!", "*ripete l'azione*", EmotionalState.EXCITED)
        ]

        # Prime parole e simboli (2-4 anni)
        self.early_preoperational_experiences = [
            ("Cosa vedi?", "Cane! Bau!", EmotionalState.EXCITED),
            ("Come ti senti?", "Felice!", EmotionalState.HAPPY),
            ("Hai fame?", "Sì, pappa!", EmotionalState.HAPPY),
            ("Chi è?", "Mamma!", EmotionalState.EXCITED),
            ("Cosa vuoi fare?", "Gioca!", EmotionalState.EXCITED)
        ]

        # Pensiero intuitivo (4-7 anni)
        self.late_preoperational_experiences = [
            ("Perché il cielo è blu?", "Perché è alto alto!", EmotionalState.CURIOUS),
            ("Cosa succede se piove?", "L'erba cresce!", EmotionalState.CURIOUS),
            ("Ti piace disegnare?", "Sì, faccio un castello!", EmotionalState.HAPPY),
            ("Hai paura del buio?", "Un po', ma ho la lucina", EmotionalState.SCARED),
            ("Raccontami della tua amica", "Giochiamo insieme alle bambole", EmotionalState.HAPPY)
        ]

    def generate_experience(self, stage: DevelopmentalStage) -> Experience:
        """Genera un'esperienza appropriata per lo stadio di sviluppo"""
        if stage == DevelopmentalStage.SENSORIMOTOR_EARLY:
            experiences = self.early_sensorimotor_experiences
        elif stage == DevelopmentalStage.SENSORIMOTOR_MID:
            experiences = self.mid_sensorimotor_experiences
        elif stage == DevelopmentalStage.SENSORIMOTOR_LATE:
            experiences = self.late_sensorimotor_experiences
        elif stage == DevelopmentalStage.PREOPERATIONAL_EARLY:
            experiences = self.early_preoperational_experiences
        else:  # PREOPERATIONAL_LATE
            experiences = self.late_preoperational_experiences

        stimulus, response, emotion = random.choice(experiences)
        
        context = {
            "time_of_day": random.choice(["morning", "afternoon", "evening"]),
            "environment": random.choice(["home", "outside", "new place"]),
            "social_context": random.choice(["alone", "with parent", "with others"]),
            "physical_state": random.choice(["rested", "tired", "hungry", "satisfied"])
        }

        return Experience(
            input_stimulus=stimulus,
            response=response,
            emotion=emotion,
            context=context,
            developmental_stage=stage,
            timestamp=time.time()
        )

    def generate_dataset(self, num_experiences: int) -> List[Experience]:
        """Genera un dataset di esperienze che segue lo sviluppo naturale"""
        experiences = []
        
        # Distribuzione delle esperienze per stadio di sviluppo
        stage_distribution = [
            (DevelopmentalStage.SENSORIMOTOR_EARLY, 0.2),    # 20% prime esperienze
            (DevelopmentalStage.SENSORIMOTOR_MID, 0.2),      # 20% sviluppo medio
            (DevelopmentalStage.SENSORIMOTOR_LATE, 0.2),     # 20% sviluppo tardivo
            (DevelopmentalStage.PREOPERATIONAL_EARLY, 0.2),  # 20% prime parole
            (DevelopmentalStage.PREOPERATIONAL_LATE, 0.2)    # 20% pensiero intuitivo
        ]

        for _ in range(num_experiences):
            stage = random.choices(
                [stage for stage, _ in stage_distribution],
                weights=[weight for _, weight in stage_distribution]
            )[0]
            experience = self.generate_experience(stage)
            experiences.append(experience)

        # Ordina per stadio di sviluppo per simulare una progressione naturale
        experiences.sort(key=lambda x: list(DevelopmentalStage).index(x.developmental_stage))
        return experiences

def save_experiences(experiences: List[Experience], filename: str):
    """Salva le esperienze in formato JSON"""
    experiences_dict = []
    for exp in experiences:
        exp_dict = {
            "input": exp.input_stimulus,
            "response": exp.response,
            "emotion": exp.emotion.value,
            "context": exp.context,
            "stage": exp.developmental_stage.value,
            "timestamp": exp.timestamp
        }
        experiences_dict.append(exp_dict)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(experiences_dict, f, indent=2)

def main():
    # Crea il generatore di esperienze
    generator = ExperienceGenerator()
    
    # Genera 1000 esperienze di sviluppo
    experiences = generator.generate_dataset(1000)
    
    # Salva le esperienze
    save_experiences(experiences, 'data/initial_experiences.json')
    
    print(f"Generate {len(experiences)} esperienze di sviluppo")
    print("\nEsempi di esperienze per ogni stadio:")
    for stage in DevelopmentalStage:
        exp = next(e for e in experiences if e.developmental_stage == stage)
        print(f"\n{stage.value}:")
        print(f"Input: {exp.input_stimulus}")
        print(f"Response: {exp.response}")
        print(f"Emotion: {exp.emotion.value}")
        print(f"Context: {exp.context}")

if __name__ == "__main__":
    main()
