# Spike structured output (Pydantic) — RISULTATO (2026-06-11)

**Domanda**: il Compilatore L1 deve passare dal parsing JSON manuale a uno schema
Pydantic validato? Con la via nativa di google-genai (`response_schema`) o con instructor?

**Risposta: sì allo schema Pydantic, e la via giusta è INSTRUCTOR** — per una ragione
non ovvia emersa dallo spike.

## I numeri (stesso prompt, stesso modello gemini-2.5-flash via Vertex, stesso regolamento)

| | Via A — nativa `response_schema` | Via B — `instructor.from_genai` |
|---|---|---|
| Parametri conformi al contratto v1 approvato | **17/17** ✓ | **17/17** ✓ |
| Escalation ambiguità art. 5.7 (decorrenza storni) | ✗ **0 escalation** (2 run su 2) | ✓ **trovata** (stato `da_verificare`, motivo corretto) |
| Clausole nel report | 21–32 | 45 (più granulare) |
| Durata / token | 53–79 s · ~3.1k/6.5k | 57 s · ~2.9k/4.6k |
| Retry su validazione | manuali (loop nostro) | automatici (`max_retries`) |

## La scoperta

Con il **constrained decoding** della via nativa (la struttura imposta token per token),
il modello diventa più "compilativo" e **smette di riflettere sulle ambiguità**: 0
escalation anche dopo aver reso la checklist un campo obbligatorio dello schema (l'ha
compilata dichiarando tutto "ok"). Con **instructor** (generazione più libera, poi
validazione Pydantic + retry sugli errori) il modello mantiene il comportamento riflessivo
e becca l'art. 5.7 esattamente come la versione prompt-only del compilatore.

Per REGOLO la capacità di dire "non sono sicuro" vale più della garanzia sintattica:
i 17/17 parametri li prendono entrambe, ma **solo instructor preserva l'abstain** — che è
il cuore del gate HITL.

**Caveat**: n=1 run per via (più il run prompt-only precedente, coerente con la B). La
misura sistematica arriva coi golden test di compilazione in Fase 1 — questo spike decide
solo la direzione tecnica.

## Cosa si porta a casa il Compilatore v1 (Fase 1)

1. **Schema Pydantic** come unica fonte della struttura (campi descritti, validatori di
   business: confidenza ∈ [0,1], coerenza checklist↔escalation, date ISO, report minimo).
2. **instructor.from_genai** sopra il client Vertex ADC già in uso (`pip install
   instructor jsonref`), `max_retries` per l'auto-correzione sugli errori di validazione.
3. La **checklist ambiguità resta sia nel prompt sia nello schema** (campo obbligatorio
   `checklist_ambiguita`): nel run B il modello l'ha percorsa per davvero.
4. Il validatore `ambiguita_coerenti` (checklist segnala → report deve escalare) è il
   tipo di regola che con instructor diventa retry automatico invece che bug silenzioso.

File: `spike_structured.py` (schema + entrambe le vie), `contratto_nativo.yaml`,
`contratto_instructor.yaml`, `esiti.json`.
