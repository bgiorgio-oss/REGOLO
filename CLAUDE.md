# REGOLO — Istruzioni per Claude Code

## Cos'è questo progetto

REGOLO è il progetto di nuova generazione per il reparto LOYALTY: disaccoppia il frontend
dal backend della piattaforma loyalty e introduce l'AI **a compile-time** nella produzione
dei dati di gara. Documento di riferimento: `docs/PRESENTAZIONE_PROGETTO.md`.

## Regola numero zero — ISOLAMENTO

- **NON toccare mai** `/Users/bgiorgio/AUTOMAZIONI/` (progetto Argo/MAGI): è un progetto
  diverso con scopi diversi. Né import, né symlink, né modifiche, né condivisione di venv,
  DB, collection Qdrant o porte.
- I pattern di AUTOMAZIONI/MAGI (HITL stile MISATO, text2sql stile IBUKI, golden test stile
  IRUEL, CRAG…) si **reimplementano** qui da zero quando servono. Mai importarli.

## Convenzioni

| Aspetto | Regola |
|---|---|
| Lingua commenti/doc | Italiano |
| Python | 3.12, venv locale `venv/` (NON `venv_global`, che è di AUTOMAZIONI) |
| Porta API demo | **8788** (8765 è MAGI in produzione — mai usarla) |
| Dipendenze | Minime: fastapi, uvicorn, pyyaml. Aggiungere solo se indispensabile |
| Determinismo | Il motore (`mockup/03_motore/`) non usa mai datetime.now()/random senza seed: la data di riferimento è una costante, i dati mock hanno seed fisso |
| Dati | Tutti i dati del mockup sono FITTIZI (generati con seed). Mai inserire dati reali di clienti o PII vera |
| Output generati | `mockup/output/` è gitignored — si rigenera con `run_demo.sh` |

## Principi architetturali vincolanti

1. **AI a compile-time, mai a runtime**: l'LLM compila il regolamento in Contratto di Gara;
   i punti li calcola SOLO il motore deterministico.
2. **Ledger append-only**: il credito non si sovrascrive, si accoda (accredito/storno/rettifica).
3. **HITL sui soldi**: nessun batch di credito diventa "contabilizzato" senza approvazione umana.
4. **Tracciabilità**: ogni regola del contratto cita la clausola del regolamento di origine
   (`fonte_clausola`); ogni evento ledger cita versione contratto e run.
5. **Effective dating**: le revisioni del regolamento diventano nuove versioni del contratto
   con finestra di validità; i ricalcoli retroattivi sono replay + conguagli espliciti.

## Struttura

Pipeline del mockup, in ordine: `00_regolamento → 01_contratto → 02_dati → 03_motore → 04_api → 05_frontend`.
Il motore scrive in `mockup/output/` (ledger.jsonl + state.json); l'API serve solo da lì.
