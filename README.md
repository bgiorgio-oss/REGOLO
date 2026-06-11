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

## Cosa puoi provare (azioni reali, persistono in `mockup/output/runtime.json`)

**Frontend punto vendita** (http://localhost:8788/) — dashboard con saldo/progressi/classifica,
**catalogo con richiesta premi** (scala il saldo, con controllo disponibilità), storico ordini,
**movimenti filtrabili + export CSV**, **assistenza/contact center** (apertura ticket, anche
contestazioni ex art. 9.2, con thread di risposta), news.

**Backoffice** (http://localhost:8788/backoffice) — panoramica con attività runtime, gare e
versioni contratto, compilazione (incl. banner AI reale), **caricamenti con drag&drop e
validazione vera** (schema/codici/anomalie vs storico), riconciliazione, what-if,
**approvazione HITL del batch giugno** (sposta davvero gli eventi a contabilizzato: i saldi
dei PV cambiano sul frontend), anagrafica con ricerca, **coda ticket con risposta**,
**pubblicazione comunicazioni** (compaiono nelle news dei PV), risoluzione alert, ledger.

Bottone **↺ Reset demo** nel backoffice per tornare allo stato iniziale.

## Cosa è reale e cosa è simulato

| Layer | Nel mockup |
|---|---|
| L1 Compilatore AI | **Reale (v0)** — `mockup/01_contratto/compilatore.py`: legge il regolamento, chiama un LLM vero (Gemini via Vertex ADC, fallback Ollama), produce contratto YAML + report con confidenze, **si auto-verifica** contro il contratto approvato a mano. Primo run: 17/17 parametri conformi, escalation automatica dell'ambiguità all'art. 5.7 |
| L2 Motore di calcolo | **Reale e deterministico** — riesegue davvero v1/v2, replay, riconciliazione |
| L3 Ledger | **Reale** — eventi append-only in `output/ledger.jsonl` |
| L4 API di serving | **Reale** — FastAPI su :8788 |
| L5 Frontend | Demo visiva (HTML/JS, dati veri dall'API) |
| L6 Control plane | Demo visiva (dati veri di riconciliazione/what-if/approvazioni + banner compilazione AI) |

## Compilazione AI reale (opzionale)

```bash
./run_demo.sh --ai          # demo completa, compilazione AI inclusa
# oppure, solo la compilazione:
venv/bin/python mockup/01_contratto/compilatore.py
```

Requisiti (uno dei due):
- **Gemini via Vertex**: `.env` con `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` e
  credenziali ADC gcloud già presenti sulla macchina (costo: centesimi a compilazione);
- **Ollama locale**: servizio attivo con almeno un modello (`ollama pull llama3.1`).

L'output va in `mockup/01_contratto/compilato_ai/` (contratto proposto, report, confronto
col v1 approvato) e compare come banner nel backoffice → Compilazione. Il contratto AI
**non** sostituisce mai il v1 approvato: nel sistema reale passerebbe dalla firma umana.
