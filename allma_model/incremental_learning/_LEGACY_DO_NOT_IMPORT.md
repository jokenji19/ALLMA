# ⚠️ QUARANTENA LEGACY — NON IMPORTARE IN PRODUZIONE

Questa cartella contiene il codice del sistema di Incremental Learning di **ALLMA V3** (training-era).

## Stato: LEGACY / ARCHIVIO

La logica attiva di apprendimento incrementale è in:
- `/allma_model/learning_system/incremental_learning.py`
- `/allma_model/learning_system/meta_learning_system.py`

## Perché non cancellare subito?

I file contengono riferimenti storici e dataset di training (`initial_experiences.json`, ~330KB) che potrebbero
servire per un futuro fine-tuning del modello base o per analisi forensi sui pattern di apprendimento.

## Regola V6

Nessun modulo in `/allma_model/core/` o `/allma_model/ui/` deve importare da questa cartella.
Sprint V6.3 (Vector Engine) deciderà definitivamente il destino di questi file.
