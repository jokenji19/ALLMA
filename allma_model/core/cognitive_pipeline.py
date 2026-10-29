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


class CognitiveValidationError(RuntimeError):
    """A required check failed or could not admit the candidate."""


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
        require_structural: bool = False,
    ):
        self.structural_core = structural_core
        self.neuroplasticity_v5 = neuroplasticity_v5
        self.identity_engine_v5 = identity_engine_v5
        self.volition_v5 = volition_v5
        self.require_structural = require_structural

    def process(
        self,
        raw_text: str,
        identity_state: Optional[Any] = None,
        *, preserve_text: bool = False,
    ) -> Tuple[str, list]:
        """
        Applica tutti i layer cognitivi in sequenza al testo grezzo dell'LLM.

        Args:
            raw_text:       Output grezzo proveniente dall'LLM.
            identity_state: Snapshot dello stato identitario calcolato all'inizio del turno.
            preserve_text: Valida senza modificare il testo; usato dalla chat
                per mantenere coerenti anteprima, risposta finale e memoria.

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
                raise CognitiveValidationError('Structural rules unavailable') from e

        if self.require_structural and self.structural_core is None:
            raise CognitiveValidationError('Structural validator unavailable')
        if self.structural_core:
            try:
                before = text
                text, is_valid, struct_violations = self.structural_core.validate(text)
                if not is_valid:
                    raise CognitiveValidationError('Structural constraints not satisfied')
                if preserve_text and text != before:
                    raise CognitiveValidationError('Structural admission would alter delivered text')
            except Exception as e:
                raise CognitiveValidationError('Structural validation failed') from e

        # --- LAYER 3: VOLITION MODULATOR (Corteccia Espressiva) ---
        # Chat style is chosen before inference. Already delivered text is
        # immutable; validation cannot silently rewrite its tone or paragraphs.
        if self.volition_v5 and identity_state and not preserve_text:
            try:
                text = self.volition_v5.apply(text, identity_state)
            except Exception as e:
                logging.warning('[CognitivePipeline] Optional expression unavailable: %s', type(e).__name__)
            if self.structural_core:
                try:
                    text, valid, extra = self.structural_core.validate(text)
                    if not valid:
                        raise CognitiveValidationError('Expression violates structural constraints')
                    struct_violations = list(dict.fromkeys(struct_violations + extra))
                except Exception as e:
                    raise CognitiveValidationError('Expression validation failed') from e

        # Admission and durable delivery happen in the host, after all gates.
        # Neither a rejected candidate nor a truncated preview changes state.
        logging.info('[CognitivePipeline] Candidate structurally checked')
        return text, struct_violations

    def commit(self, text, violations):
        """Observe only an admitted, completed, durably stored answer."""
        outcomes = {}
        for name, component, method, args in (
            ('neuroplasticity', self.neuroplasticity_v5, 'analyze', (violations,)),
            ('identity_state', self.identity_engine_v5, 'update_state', (text, violations)),
        ):
            if component is None:
                continue
            try:
                getattr(component, method)(*args)
                outcomes[name] = 'saved'
            except Exception as error:
                outcomes[name] = 'failed'
                logging.warning('[CognitivePipeline] %s commit failed: %s', name, type(error).__name__)
        return outcomes

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
