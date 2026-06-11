# REGOLO — Roadmap operativa

*File di lavoro: si aggiorna a ogni avanzamento. La versione "da presentazione" è in
`docs/PRESENTAZIONE_PROGETTO.md` §9; il piano dettagliato della fase corrente è anche
sul Desktop («REGOLO - Piano Operativo Fasi.html»).*

**Legenda**: ✅ fatto · 🔄 in corso · ⬜ da fare · 🤝 serve input/decisione di Giorgio

---

## Fase 0 — Mockup e presentazione ✅ (completata il 2026-06-10)

- ✅ Ambiente nuovo e isolato (`~/REGOLO`, venv proprio, porta 8788 — mai 8765/MAGI)
- ✅ Documento di presentazione (`docs/PRESENTAZIONE_PROGETTO.md` + versione grafica su Desktop)
- ✅ Regolamento fittizio stile Spazio Enel (12 articoli, 2 ambiguità pilotate)
- ✅ Contratto di Gara v1+v2 (YAML, effective dating) + report di compilazione simulato
- ✅ Motore deterministico REALE: punti/cap/bonus/storni, ledger append-only (392 eventi),
  riconciliazione con diagnosi automatica (23/25 OK, 2 KO spiegate), quarantena anomalie,
  what-if retroattivo (+6.750 pt / +1.687,50 €)
- ✅ API di serving FastAPI (:8788) + frontend utente + backoffice
- ✅ Verifica manuale dei conti (SE-MI-001 voce per voce)
- ✅ **Compilatore L1 v0 REALE** (2026-06-11): Gemini 2.5 Flash via Vertex ADC su `.env`
  proprio di REGOLO — 17/17 parametri conformi al contratto approvato, escalation
  automatica dell'ambiguità art. 5.7 (decorrenza storni) grazie alla checklist ambiguità
  nel prompt; banner risultati nel backoffice; `./run_demo.sh --ai`
- ✅ **Compilatore v0.2** (2026-06-11): schema Pydantic condiviso (`schema_contratto.py`)
  + instructor con retry + **input PDF/DOCX** (pronto per i regolamenti reali). Run di
  verifica: 17/17 + escalation art. 9.2 ("dalla pubblicazione": decorrenza vaga — vera).
  Nota: la rilevazione ambiguità varia da run a run (5.7 vs 9.2) → in Fase 1 servono
  più passaggi/doppio modello con unione delle escalation
- ✅ **Golden test harness a doppio motore** (2026-06-11): `tests/golden/` — 17 casi
  limite da regolamento (cap esatto/superato, storni fuori cap, bonus al netto, tripletta,
  mese parziale, effective dating v1/v2) eseguiti su motore Python E ZEN/JDM: **17/17
  verdi su entrambi**. È il collaudo che accompagnerà ogni modifica
- ✅ **Decisione ledger L3** (2026-06-11): Fase 1 = tabella append-only SQLite fatta in
  casa (WAL, trigger anti-UPDATE/DELETE, storni compensativi); Fase 2+ = stessa tabella
  su Postgres; Formance solo se servirà double-entry vero. Fatti e fonti:
  `docs/DECISIONE_LEDGER.md`

**Uscita fase**: decisione go/no-go interna → 🤝 presentare la demo e decidere

---

## Fase 1 — Shadow mode su una gara reale (6–8 settimane) ⬜

Obiettivo: dimostrare l'affidabilità del calcolo a **rischio zero**, in parallelo alla
PIATTAFORMA, su una gara vera già attiva.

### Blocco 1.1 — Setup e materiale (settimane 1–2)
- 🤝 Scegliere la **gara pilota** (criteri: regolamento già stabile, dati mensili regolari,
  cliente non ostile a confronti)
- 🤝 Raccogliere su Drive **2–3 regolamenti reali** (pilota + 1–2 per varietà di meccaniche)
- 🤝 Censire gli **accessi**: export punteggi/prestazioni della piattaforma per la gara
  pilota (gli scarichi notturni esistono già in AUTOMAZIONI: qui si REPLICA il pattern,
  non si importa il codice)
- ⬜ Estendere lo **schema del Contratto di Gara** alle meccaniche reali incontrate
  (gare a obiettivo, classifiche, raccolte punti, instant win, …)
- ⬜ Decidere dove gira la Fase 1: Mac (semplice) vs Cloud Run (progetto GCP separato) → 🤝

### Blocco 1.2 — Compilatore v1 (settimane 3–4)
- ⬜ Pipeline compilazione: estrazione testo (PDF/DOCX) → structured output su schema →
  report di compilazione con confidenze → escalation clausole dubbie
  *(bozza v0 già funzionante nel mockup: `mockup/01_contratto/compilatore.py` — da
  estendere: input PDF/DOCX, checklist ambiguità dalla KB, doppio modello)*
- ✅ **Spike structured output** (2026-06-11): schema Pydantic + **instructor** scelto
  sulla via nativa `response_schema` — entrambe 17/17 sui parametri, ma il constrained
  decoding nativo sopprime le escalation di ambiguità (0/2 run), instructor le preserva
  (art. 5.7 trovato). Dettagli: `spikes/instructor/RISULTATO.md`
- 🤝 Scegliere il modello LLM e il billing (Gemini su GCP nuovo progetto / altro)
- ⬜ Anonimizzazione sistematica: nessuna PII nei prompt (il compilatore lavora su regole)
- ⬜ Compilare il regolamento della gara pilota → contratto v1 **approvato a mano**
- ⬜ **Golden test di gara**: 15–30 casi (input → punteggio atteso) derivati dal
  regolamento, inclusi i casi limite; verdi prima di procedere

### Blocco 1.3 — Motore e riconciliazione (settimane 5–6)
- ✅ **Spike GoRules ZEN Engine** (2026-06-11): contratto SAM2026 transpilato in JDM ed
  eseguito — **392/392 celle identiche al motore, zero divergenze, 0,53 ms/valutazione**
  (`spikes/zen/RISULTATO.md`). Decisione: in Fase 1 L2 = ZEN + nostro layer effective
  dating/replay; il motore Python del mockup resta come doppio controllo (golden test)
- ⬜ Adattare il motore alle meccaniche del contratto pilota (parametrico, zero hardcode)
- ⬜ Ledger su DB: **deciso** — tabella append-only SQLite (schema in
  `docs/DECISIONE_LEDGER.md`) + run replay-abili
- ⬜ Job notturno di riconciliazione: REGOLO vs export piattaforma, con diagnosi automatica
- ⬜ Report divergenze leggibile (riusare la vista backoffice del mockup)

### Blocco 1.4 — Collaudo (settimane 7–8)
- ⬜ 3 cicli mensili (o settimanali, se i dati lo permettono) di riconciliazione
  **verde o con divergenze tutte spiegate**
- ⬜ Report finale di fase: affidabilità misurata, costi LLM misurati, raccomandazione
- 🤝 Decisione go/no-go Fase 2

**Criterio di uscita**: riconciliazione verde per 3 cicli consecutivi + golden test verdi.

---

## Fase 2 — Backend takeover gare nuove (2–3 mesi) ⬜

- ⬜ Verifica write-back: endpoint `/json/*.php` della piattaforma in **scrittura**
  (in lettura già provati in produzione altrove); fallback automazione browser
- ⬜ Control plane operativo: coda approvazioni HITL, alert qualità dati
- ⬜ API di serving v1 (multi-gara, multi-cliente)
- ⬜ 1–2 gare nuove gestite end-to-end (punteggi e credito prodotti da REGOLO,
  piattaforma solo visualizzazione)

## Fase 3 — Frontend pilota (2–3 mesi, in parallelo a Fase 2) ⬜

- ⬜ Frontend white-label (sviluppo interno) su API di serving
- 🤝 Scelta cliente pilota
- ⬜ Tema/branding per cliente + widget derivati dal contratto

## Fase 4 — Decommissioning progressivo ⬜

- ⬜ Migrazione cliente per cliente a scadenza gara/contratto
- ⬜ Fascicolo di audit storico per ogni cliente migrato

---

## Registro decisioni

| Data | Decisione |
|---|---|
| 2026-06-10 | AI a compile-time (mai a runtime sui calcoli) — confermato da Giorgio |
| 2026-06-10 | Isolamento totale da AUTOMAZIONI/MAGI: reimplementare i pattern, mai importare |
| 2026-06-10 | Frontend: sviluppo interno confermato |
| 2026-06-11 | Motore L2 in Fase 1 = GoRules ZEN Engine (JDM) + nostro layer effective dating/replay — validato da spike con equivalenza 392/392 vs motore proprio |
| 2026-06-11 | Compilatore L1 in Fase 1 = schema Pydantic + instructor (NON response_schema nativo: il constrained decoding sopprime le escalation di ambiguità — vedi spike) |
| 2026-06-11 | Ledger L3 = tabella append-only fatta in casa (SQLite → Postgres); niente Formance/Blnk/TigerBeetle in Fase 1 — `docs/DECISIONE_LEDGER.md` |
| 2026-06-11 | La rilevazione ambiguità del compilatore varia tra run: in Fase 1 escalation = UNIONE di più passaggi/modelli, mai un run singolo |
