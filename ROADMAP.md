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
- 🤝 Scegliere il modello LLM e il billing (Gemini su GCP nuovo progetto / altro)
- ⬜ Anonimizzazione sistematica: nessuna PII nei prompt (il compilatore lavora su regole)
- ⬜ Compilare il regolamento della gara pilota → contratto v1 **approvato a mano**
- ⬜ **Golden test di gara**: 15–30 casi (input → punteggio atteso) derivati dal
  regolamento, inclusi i casi limite; verdi prima di procedere

### Blocco 1.3 — Motore e riconciliazione (settimane 5–6)
- ⬜ Adattare il motore alle meccaniche del contratto pilota (parametrico, zero hardcode)
- ⬜ Ledger su DB (SQLite per la fase 1 basta) + run replay-abili
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
