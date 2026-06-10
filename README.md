# REGOLO — Regolamento Eseguibile

> **Il regolamento è il codice sorgente.**
> L'AI lo compila in un contratto eseguibile, un motore deterministico lo esegue,
> il frontend diventa un guscio leggero che legge da un'API.

REGOLO è il progetto di disaccoppiamento frontend/backend della piattaforma loyalty
e di introduzione dell'AI a **compile-time** nella produzione di tutti i dati di gara
(punteggi, credito, anagrafica, classifiche).

**Progetto indipendente**: non condivide codice, dati o servizi con `AUTOMAZIONI/` (Argo/MAGI).
I pattern validati lì vengono *reimplementati* qui, mai importati.

---

## Contenuto

| Percorso | Cosa contiene |
|---|---|
| `docs/PRESENTAZIONE_PROGETTO.md` | **Il documento di presentazione del progetto** (visione, architettura, roadmap, rischi) |
| `mockup/` | Dimostrazione end-to-end funzionante (vedi sotto) |

## Il mockup in 30 secondi

Una gara incentive fittizia — **"Spazio alla Meta 2026"**, canale Spazio Enel Partner — percorsa per intero:

```
00_regolamento/   il regolamento di gara (documento, fonte di verità)
01_contratto/     il Contratto di Gara compilato dall'AI (YAML v1 + v2) + report di compilazione
02_dati/          anagrafica punti vendita, prestazioni mensili, export della piattaforma legacy
03_motore/        il motore deterministico: calcola punti, bonus, storni, classifiche,
                  riconciliazione con la piattaforma, what-if retroattivo → ledger + stato
04_api/           API di serving (FastAPI) — il "backend headless"
05_frontend/      frontend utente finale + backoffice (control plane), HTML/JS puro
output/           generato dal motore: ledger.jsonl + state.json (gitignored)
```

## Avvio rapido

```bash
cd ~/REGOLO
./run_demo.sh
```

Poi apri:

- **Frontend utente finale** → http://localhost:8788/
- **Backoffice / control plane** → http://localhost:8788/backoffice

> Porta **8788** scelta apposta per non collidere con MAGI (8765).

## Cosa è reale e cosa è simulato

| Layer | Nel mockup |
|---|---|
| L1 Compilatore AI | **Simulato** (lo YAML è scritto a mano "come lo produrrebbe l'AI", con report di compilazione, confidence e clausole escalate a umano) |
| L2 Motore di calcolo | **Reale e deterministico** — riesegue davvero v1/v2, replay, riconciliazione |
| L3 Ledger | **Reale** — eventi append-only in `output/ledger.jsonl` |
| L4 API di serving | **Reale** — FastAPI su :8788 |
| L5 Frontend | Demo visiva (HTML/JS, dati veri dall'API) |
| L6 Control plane | Demo visiva (dati veri di riconciliazione/what-if/approvazioni) |
