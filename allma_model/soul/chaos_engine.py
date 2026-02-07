import math
import random
from dataclasses import dataclass

@dataclass
class ChaosParameters:
    sigma: float = 10.0
    rho: float = 28.0
    beta: float = 8.0 / 3.0
    dt: float = 0.01

class ChaosEngine:
    """
    Generatore di Caos Deterministico basato sull'Attrattore di Lorenz.
    Fornisce un'evoluzione dello stato che è:
    1. Deterministica (stesse condizioni iniziali -> stesso risultato)
    2. Imprevedibile a lungo termine (sensibile alle condizioni iniziali)
    3. Limitata (bounded) in uno spazio di fase specifico
    """
    def __init__(self, seed: float = None):
        if seed:
            random.seed(seed)
        
        # Stato iniziale casuale ma vicino all'attrattore
        self.x = random.uniform(0.1, 1.0)
        self.y = random.uniform(0.1, 1.0)
        self.z = random.uniform(0.1, 1.0)
        
        self.params = ChaosParameters()
        
    def step(self, perturbation: float = 0.0) -> tuple[float, float, float]:
        """
        Esegue un passo di integrazione temporale (Eulero o RK4).
        
        Args:
            perturbation: Un valore esterno (es. emozione utente) che "urti" il sistema
        """
        dt = self.params.dt
        
        # Se c'è perturbazione, influenziamo le variabili di stato
        if perturbation != 0.0:
            self.x += perturbation * 0.1
        
        # Equazioni di Lorenz
        # dx/dt = sigma * (y - x)
        dx = self.params.sigma * (self.y - self.x)
        
        # dy/dt = x * (rho - z) - y
        dy = self.x * (self.params.rho - self.z) - self.y
        
        # dz/dt = x * y - beta * z
        dz = self.x * self.y - self.params.beta * self.z
        
        # Integrazione (Eulero semplice per performance)
        self.x += dx * dt
        self.y += dy * dt
        self.z += dz * dt
        
        return self.x, self.y, self.z

    def get_normalized_state(self) -> tuple[float, float, float]:
        """
        Restituisce lo stato normalizzato tra -1.0 e 1.0 (approssimativamente).
        L'attrattore di Lorenz oscilla tipicamente tra -20 e 20 per x/y e 0-50 per z.
        """
        # Normalizzazione empirica per Lorenz standard
        norm_x = math.tanh(self.x / 10.0)
        norm_y = math.tanh(self.y / 15.0)
        norm_z = math.tanh((self.z - 25.0) / 15.0) # Centrato su 25
        
        return norm_x, norm_y, norm_z
