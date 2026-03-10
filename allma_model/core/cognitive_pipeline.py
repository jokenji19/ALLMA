"""
CognitivePipeline — ALLMA V6 Sprint 1

Responsabile della catena di validazione e modulazione del testo
generato dall'LLM prima che venga inviato all'utente.

Separa il "cosa penso" (LLM) dal "come lo esprimo" (Pipeline V5 Layers).

Layers in sequenza:
    1. StructuralCore     → Validazione vincoli etici e strutturali
    2. NeuroplasticityV5  → Rinforzo plastico basato sulle violazioni
    3. IdentityStateV5    → Aggiornamento stato identitario post-risposta
    4. VolitionV5         → Modulazione espressiva in base all'umore
"""

from __future__ import annotations
import logging
import re
from typing import Optional, Any, Tuple


class CognitivePipeline:
    """
    Catena di post-elaborazione del testo LLM.

    Interfaccia di produzione:
        result_text = pipeline.process(raw_llm_text, identity_state)

    Usage in allma_core.py (dentro il blocco LLM):
        from allma_model.core.cognitive_pipeline import CognitivePipeline
        pipeline = CognitivePipeline(
            structural_core=self.structural_core,
            neuroplasticity_v5=self.neuroplasticity_v5,
            identity_engine_v5=self.identity_engine_v5,
            volition_v5=self.volition_v5,
        )
        response_text, struct_violations = pipeline.process(response_text, identity_state)
    """

    def __init__(
        self,
        structural_core: Optional[Any] = None,
        neuroplasticity_v5: Optional[Any] = None,
        identity_engine_v5: Optional[Any] = None,
        volition_v5: Optional[Any] = None,
    ):
        self.structural_core = structural_core
        self.neuroplasticity_v5 = neuroplasticity_v5
        self.identity_engine_v5 = identity_engine_v5
        self.volition_v5 = volition_v5

    def process(
        self,
        raw_text: str,
        identity_state: Optional[Any] = None,
    ) -> Tuple[str, list]:
        """
        Applica tutti i layer cognitivi in sequenza al testo grezzo dell'LLM.

        Args:
            raw_text:       Output grezzo proveniente dall'LLM.
            identity_state: Snapshot dello stato identitario calcolato all'inizio del turno.

        Returns:
            (processed_text, struct_violations): Testo finale + lista violazioni rilevate.
        """
        text = raw_text
        struct_violations = []

        # --- LAYER 1: STRUCTURAL CORE (Midollo) ---
        if self.neuroplasticity_v5 and self.structural_core:
            try:
                active_rules = self.neuroplasticity_v5.get_active_rules()
                self.structural_core.update_rules(active_rules)
            except Exception as e:
                logging.warning(f"[CognitivePipeline] Neuroplasticity sync failed: {e}")

        if self.structural_core:
            try:
                text, is_valid, struct_violations = self.structural_core.validate(text)
                if not is_valid:
                    logging.warning(f"[CognitivePipeline] StructuralCore corrected: {struct_violations}")
            except Exception as e:
                logging.error(f"[CognitivePipeline] StructuralCore validate failed: {e}")

        # --- LAYER 4: NEUROPLASTICITY (Rinforzo Plastico) ---
        if self.neuroplasticity_v5:
            try:
                self.neuroplasticity_v5.analyze(struct_violations)
            except Exception as e:
                logging.warning(f"[CognitivePipeline] Neuroplasticity analyze failed: {e}")

        # --- LAYER 2: IDENTITY STATE UPDATE ---
        if self.identity_engine_v5:
            try:
                self.identity_engine_v5.update_state(
                    validated_text=text,
                    violations=struct_violations,
                )
            except Exception as e:
                logging.warning(f"[CognitivePipeline] IdentityState update failed: {e}")

        # --- LAYER 3: VOLITION MODULATOR (Corteccia Espressiva) ---
        if self.volition_v5 and identity_state:
            try:
                text = self.volition_v5.apply(text, identity_state)
            except Exception as e:
                logging.warning(f"[CognitivePipeline] Volition apply failed: {e}")

        logging.info(f"[CognitivePipeline] ✅ Processed: {text[:60]}...")
        return text, struct_violations

    def attach_modules(
        self,
        structural_core=None,
        neuroplasticity_v5=None,
        identity_engine_v5=None,
        volition_v5=None,
    ):
        """Permette di collegare i moduli V5 dopo l'inizializzazione (lazy binding)."""
        if structural_core is not None:
            self.structural_core = structural_core
        if neuroplasticity_v5 is not None:
            self.neuroplasticity_v5 = neuroplasticity_v5
        if identity_engine_v5 is not None:
            self.identity_engine_v5 = identity_engine_v5
        if volition_v5 is not None:
            self.volition_v5 = volition_v5
