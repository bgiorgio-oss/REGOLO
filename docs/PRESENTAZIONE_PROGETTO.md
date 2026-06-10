# REGOLO — Regolamento Eseguibile

### Documento di presentazione del progetto

| | |
|---|---|
| **Reparto** | Loyalty — H&A Motivation Company |
| **Stato documento** | Bozza v1 per discussione interna |
| **Data** | 10 giugno 2026 |
| **Allegato** | Mockup end-to-end funzionante in `mockup/` (gara fittizia "Spazio alla Meta 2026") |

> **In una frase**: trattare il regolamento di gara come *codice sorgente* — l'AI lo compila
> in un contratto eseguibile, un motore deterministico lo esegue, e il frontend diventa un
> guscio leggero e personalizzabile che legge da un'API. La PIATTAFORMA attuale non viene
> sostituita di colpo: viene progressivamente svuotata.

---

## 1. Executive summary

Oggi la PIATTAFORMA gestisce in un unico blocco sia il frontend per l'utente finale
(performance, comunicazioni, credito, cataloghi, contact center) sia il backend operativo
(creazione gare, HIE prodotto, anagrafica, cluster, caricamento prestazioni e credito).
Ogni gara nasce da un regolamento, ma la traduzione del regolamento in configurazione di
piattaforma è manuale, rigida e fragile: **quando il regolamento cambia in corso d'opera —
e cambia sempre — le implementazioni necessarie possono essere troppe, troppo lente o
semplicemente non fattibili.**

REGOLO propone tre mosse:

1. **Il regolamento diventa la fonte di verità eseguibile.** Un compilatore AI legge il
   documento e produce il **Contratto di Gara**: una specifica strutturata, versionata e
   approvata da un umano, in cui ogni regola cita la clausola di origine.
2. **Il calcolo esce dalla piattaforma.** Un motore deterministico (zero AI a runtime)
   applica il contratto ai dati di prestazione e produce punteggi, bonus, storni e credito
   come **eventi su un ledger append-only**. Una revisione di regolamento diventa: nuova
   versione del contratto → replay → diff visibile → conguagli espliciti. Niente più change
   request alla piattaforma.
3. **Il frontend si stacca.** Un'API di serving espone saldi, classifiche, progressi e
   cataloghi a qualunque interfaccia: il nuovo frontend white-label sviluppato in casa,
   e nel transitorio la PIATTAFORMA stessa, che riceve i dati già calcolati e degrada a
   strato di visualizzazione.

La migrazione è a fasi (strangler), parte in **shadow mode** su una gara reale a rischio
zero, e ogni fase ha un criterio di uscita misurabile. Il mockup allegato dimostra l'intero
ciclo su una gara fittizia ispirata al canale Spazio Enel.

---

## 2. Il problema oggi

### 2.1 Cosa fa la PIATTAFORMA

| Lato | Funzioni |
|---|---|
| **Frontend** (utente finale) | Visualizzazione performance, comunicazioni, caricamento credito, spesa credito, cataloghi premi, contact center |
| **Backend** (operations) | Creazione gare e concorsi, HIE prodotto (valorizzazione punti), anagrafica, gestione cluster, caricamento dati di prestazione, caricamento credito |

### 2.2 I tre dolori strutturali

1. **Rigidità alle variazioni in corso d'opera.** La piattaforma viene strutturata a inizio
   progetto sulla definizione iniziale di gare e operazioni. Ogni variazione successiva è
   un'implementazione: a volte lenta, a volte costosa, a volte impossibile.
2. **Accoppiamento frontend/backend.** Non si può personalizzare l'esperienza utente senza
   toccare la macchina delle meccaniche, e viceversa. Ogni cliente vorrebbe un frontend
   diverso; la piattaforma ne offre uno.
3. **Il regolamento e la piattaforma vivono in mondi separati.** Il documento che definisce
   legalmente la gara viene interpretato a mano e trascritto in configurazioni. Nessun
   legame verificabile tra clausola e numero mostrato all'utente.

### 2.3 Il vincolo di contesto

Le manifestazioni a premio in Italia sono materia regolata (DPR 430/2001): il regolamento è
un documento con valore legale e i punteggi devono essere difendibili in caso di
contestazione. Qualunque soluzione deve **aumentare** l'auditabilità, non ridurla.

---

## 3. La visione

```
   OGGI                                    DOMANI
   ────                                    ──────
   Regolamento (doc)                       Regolamento (doc, versionato)
        │ interpretazione umana                 │ COMPILAZIONE (AI + approvazione umana)
        ▼                                       ▼
   Configurazione manuale              Contratto di Gara (spec eseguibile, vN)
   della PIATTAFORMA                            │ esecuzione deterministica
        │                                       ▼
        ▼                                  Ledger eventi (punti, credito)
   La piattaforma calcola                       │
   e mostra (monolite)                          ▼
                                           API di serving
                                            │         │
                                            ▼         ▼
                                     Frontend     PIATTAFORMA legacy
                                     white-label  (solo visualizzazione,
                                     in casa      finché serve)
```

L'AI entra **dove rende**: leggere documenti, interpretare clausole, proporre mapping,
individuare anomalie, generare configurazioni e contenuti. L'AI **non entra** dove
servono determinismo e difendibilità: il calcolo di punti e credito.

---

## 4. Principi non negoziabili

| # | Principio | Conseguenza pratica |
|---|---|---|
| P1 | **AI a compile-time, mai a runtime** | L'LLM produce il Contratto di Gara (una volta, più le revisioni). I punteggi li calcola solo il motore deterministico. Stesso input → stesso output, sempre. Costi AI: solo a compilazione, non per transazione |
| P2 | **Determinismo e replay** | Ogni run del motore registra versione contratto + hash input + output. Qualunque numero è riproducibile a distanza di anni |
| P3 | **Ledger append-only** | Il credito è denaro: mai sovrascritto, solo movimentato (accredito, storno, rettifica, spesa). I saldi sono somme di eventi |
| P4 | **Human-in-the-loop sui soldi** | Nessun batch di credito viene contabilizzato senza approvazione esplicita. L'AI propone, un umano firma |
| P5 | **Tracciabilità clausola → numero** | Ogni regola del contratto cita l'articolo del regolamento; ogni evento ledger cita regola, versione contratto e run. Catena completa: documento → regola → evento → saldo |
| P6 | **Isolamento da AUTOMAZIONI/MAGI** | REGOLO è un progetto nuovo in un ambiente nuovo. I pattern già validati altrove (HITL, text2sql, golden test, CRAG) vengono **reimplementati**, mai importati. Nessuna condivisione di codice, venv, DB, porte |
| P7 | **Strangler, mai big-bang** | La PIATTAFORMA non si spegne: si svuota una funzione alla volta, ogni passo reversibile e misurato |

---

## 5. Architettura a sei layer

```
            REGOLAMENTO.docx (fonte di verità, versionato)
                    │
        ┌───────────▼───────────┐
   L1   │ COMPILATORE (AI+HITL) │  estrazione + KB gare passate + structured output
        │ regolamento → contratto│  + confidence/escalation + approvazione umana
        └───────────┬───────────┘
                    │ Contratto di Gara v1, v2, … (YAML/JSON, effective dating)
        ┌───────────▼───────────┐
   L2   │ MOTORE DETERMINISTICO │  applica formule, cap, bonus, storni, cluster.
        │                       │  Zero LLM. Replay-abile. Quarantena anomalie.
        └───────────┬───────────┘
                    │ eventi
        ┌───────────▼───────────┐
   L3   │ LEDGER (append-only)  │  ogni movimento = evento immutabile con riferimento
        │ punti & credito       │  a regola, versione contratto, run, stato approvazione
        └───────────┬───────────┘
                    │
        ┌───────────▼───────────┐      ┌──────────────────────────┐
   L4   │ API DI SERVING        │◄─────│ L6 CONTROL PLANE         │
        │ saldi, classifiche,   │      │ approvazioni HITL,       │
        │ progressi, cataloghi  │      │ riconciliazione, what-if,│
        └───────┬───────┬───────┘      │ alert qualità dati       │
                │       │              └──────────────────────────┘
        ┌───────▼──┐ ┌──▼────────────────┐
   L5   │ FRONTEND │ │ PIATTAFORMA legacy │  write-back via endpoint /json/*.php
        │ headless │ │ (transitorio)      │  (fallback: automazione browser)
        └──────────┘ └───────────────────┘
```

### L1 — Compilatore di Regolamenti (AI + HITL)

- **Input**: regolamento (PDF/DOCX) + KB delle gare passate (pattern di meccaniche già visti).
- **Pipeline**: estrazione testo → retrieval di meccaniche simili → structured output su
  schema rigido → autovalutazione di confidenza clausola per clausola.
- **Gestione ambiguità**: le clausole sotto soglia di confidenza NON vengono interpretate
  d'ufficio: finiscono in `clausole_da_verificare` e bloccano l'attivazione finché un umano
  (o il cliente) non scioglie il dubbio. La risoluzione resta agli atti nel report di
  compilazione.
- **Output**: il Contratto di Gara + il **report di compilazione** (clausola per clausola:
  testo estratto, interpretazione, confidenza, chi ha verificato).
- **Doppio controllo per gare critiche**: compilazione con due modelli indipendenti e
  confronto incrociato delle interpretazioni prima della review umana.

### L2 — Motore deterministico

- Esegue il contratto sui dati di prestazione: punti per unità, cap, moltiplicatori
  temporali, bonus condizionali, storni, classifiche per cluster.
- **Effective dating**: ogni versione del contratto ha una finestra di validità; il motore
  applica la versione giusta per ciascun periodo.
- **Replay**: ricalcolo integrale con qualunque versione su qualunque finestra → usato per
  what-if, conguagli e audit.
- **Quarantena**: input anomali (es. valori fuori scala rispetto allo storico) vengono
  esclusi e segnalati, non calcolati.
- Tecnologie candidate: Python + DuckDB/Polars. Nel mockup: Python puro, già deterministico.

### L3 — Ledger

- Eventi immutabili: `accredito | storno | bonus | rettifica | premio_classifica | spesa`.
- Ogni evento porta: gara, partecipante, periodo, meccanica, punti, versione contratto,
  run id, **stato** (`in_approvazione` → `contabilizzato`).
- I saldi non esistono come dato: sono viste calcolate dagli eventi. Una revisione
  retroattiva genera eventi di rettifica espliciti, mai riscritture.

### L4 — API di serving

- Il "backend headless": REST (FastAPI) che espone saldi, movimenti, progressi vs target,
  classifiche, cataloghi, comunicazioni.
- Unica porta di accesso ai dati per **tutti** i consumatori: nuovo frontend, PIATTAFORMA
  legacy, DEM, export, contact center.
- Multi-tenant per design: gara e cliente sono dimensioni di ogni endpoint.

### L5 — Frontend headless (sviluppo interno confermato)

- Codebase unica componibile + tema per cliente (branding, copy, widget).
- La configurazione dei widget **deriva dal Contratto di Gara**: se la gara ha classifiche
  per cluster, il widget classifica appare già configurato; se ha cataloghi, idem.
- Personalizzare l'esperienza di un cliente = modificare tema/composizione, non meccaniche.

### L6 — Control plane (backoffice operations)

- Coda approvazioni HITL (batch credito, contratti, mapping anagrafica/HIE).
- **Riconciliazione continua** con la PIATTAFORMA finché esiste (shadow mode permanente).
- **Simulatore what-if**: regolamento bozza + dati storici → distribuzione punti e costo
  premi *prima* di firmare. Utile anche in fase commerciale/preventivo.
- Alert qualità dati (file prestazioni fuori scala, anagrafiche duplicate, storni anomali).

---

## 6. Il Contratto di Gara

È l'artefatto centrale del progetto: la versione eseguibile del regolamento.

### 6.1 Ciclo di vita

```
bozza regolamento ──► COMPILAZIONE ──► review clausole ──► APPROVAZIONE ──► contratto v1 ATTIVO
                          ▲    (confidence + escalation)   (umano, firma)        │
                          │                                                      │ revisione
revisione regolamento ────┴──────────────────────────────────────────────► contratto v2
                                                                  (effective dating + replay
                                                                   + diff + conguagli espliciti)
```

### 6.2 Struttura (schema sintetico)

| Sezione | Contenuto | Esempio |
|---|---|---|
| `meta` | Identità, versione, finestra validità, hash del documento fonte, chi ha approvato e quando | `contratto_versione: 2, valido_dal: 2026-06-01` |
| `destinatari` | Chi partecipa e con quali requisiti | punti vendita aderenti, attivi |
| `cluster` | Criteri di segmentazione e target per cluster | GOLD/SILVER/BRONZE con target mensile |
| `kpi` | Le grandezze misurate | attivazioni luce/gas, fibra, fotovoltaico… |
| `meccaniche` | Le regole di punteggio: punti per unità, cap, moltiplicatori, bonus condizionali, storni — ognuna con `fonte_clausola` | `punti: 10, cap_mensile_punti: 600, fonte_clausola: art. 5.1` |
| `classifica_finale` | Ambito, indice di ordinamento, premi | top 3 per cluster |
| `valorizzazione` | Tasso punti→euro, catalogo, cadenza accrediti | `0,25 €/punto, accredito mensile previa validazione` |
| `caricamenti` | Flussi dati attesi e finestre di contestazione | mensile entro il 5, contestazioni 30 gg |
| `clausole_da_verificare` | Ambiguità aperte: **bloccanti** per l'attivazione | vuoto a contratto attivo |

Esempio completo: `mockup/01_contratto/gara_spazio_alla_meta.v1.yaml` e `.v2.yaml`.

### 6.3 Il caso che oggi fa male: la revisione in corso d'opera

Scenario reale (riprodotto nel mockup): a fine maggio il promotore alza il cap mensile e i
punti del fotovoltaico per spingere le vendite.

| Oggi (PIATTAFORMA) | Domani (REGOLO) |
|---|---|
| Richiesta di modifica al fornitore, analisi fattibilità, sviluppo, test, rilascio. Rischio: "non fattibile" | Ricompilazione del regolamento rivisto → contratto v2 con `valido_dal` |
| Effetto retroattivo: ricalcoli manuali su Excel, rischio errori | Replay del motore: diff per partecipante e per budget visibile **prima** di approvare; conguagli come eventi espliciti |
| Nessuna traccia del perché un saldo è cambiato | Ledger: ogni rettifica cita contratto v2 e run |

---

## 7. Flussi operativi principali

**A — Nuova gara.** Regolamento → compilazione (minuti) → review clausole dubbie →
approvazione → contratto attivo → frontend già configurato dai metadati del contratto →
simulazione su dati storici per validare i budget premi.

**B — Caricamento mensile prestazioni.** File dal cliente → controlli qualità (schema,
fuori scala vs storico → quarantena) → run del motore → eventi `in_approvazione` →
review del batch nel control plane (totali, anomalie, confronto col mese precedente) →
approvazione → eventi `contabilizzati` → visibili su frontend e write-back alla PIATTAFORMA.

**C — Revisione del regolamento in corso d'opera.** Vedi §6.3: ricompilazione → v2 →
replay → diff → approvazione → conguagli.

**D — Contestazione di un partecipante.** Dal saldo si risale agli eventi, dagli eventi
alla meccanica, dalla meccanica alla clausola del regolamento (articolo e testo). Risposta
documentata in minuti, difendibile ai sensi del DPR 430/2001.

**E — Chiusura gara.** Congelamento dati → run finale → classifiche definitive → premi
classifica come eventi → report di chiusura (audit completo: tutte le versioni contratto,
tutti i run, tutte le approvazioni).

---

## 8. Cosa riusiamo dell'esperienza già fatta (senza toccarla)

`AUTOMAZIONI/` (Argo) e MAGI **non vengono toccati né riusati come codice**: restano
progetti separati con scopi diversi. Sono però il *laboratorio* che ha già validato i
pattern chiave di REGOLO — il rischio tecnologico è quindi basso:

| Pattern validato (dove) | Cosa dimostra | Cosa ne replichiamo in REGOLO |
|---|---|---|
| Estrazione AI da regolamento (LoyaltyManager/EnelManager) | Un LLM estrae in modo affidabile campi strutturati dai regolamenti reali | Il Compilatore L1, con schema molto più ricco |
| Interrupt + approvazione umana (MISATO/KAWORU in MAGI) | L'HITL su grafo funziona in produzione | Gate di approvazione su contratti e batch credito |
| Grading di confidenza e abstain (CRAG/FUYUTSUKI) | L'AI può dire "non sono sicura" invece di inventare | `clausole_da_verificare` bloccanti |
| NL→SQL + esecuzione sandbox (IBUKI, data_engine) | L'AI può *generare* logica che poi gira deterministica | Generazione assistita delle formule del contratto |
| Benchmark notturno con golden set (IRUEL) | La regressione automatica su qualità è sostenibile | **Golden test di gara**: casi input→punteggio attesi, eseguiti a ogni modifica |
| Scarico server-side via endpoint `/json/*.php` (scarico_dati_server) | La PIATTAFORMA è pilotabile via HTTP senza fornitore, già in produzione per la lettura | Il **write-back** dei dati calcolati verso la piattaforma legacy |
| Automazione browser dei moduli piattaforma (ConfiguratorePiattaforme) | Esiste un fallback robusto dove gli endpoint non bastano | Driver di riserva per il write-back |
| Anonimizzazione PII, tracking costi, peer review a due modelli (core/) | Igiene operativa già rodata | Reimplementazione dei tre pattern |
| Cloud Run + Scheduler + Secret Manager (infra MAGI) | Deploy serverless a costo quasi nullo | Stessa piattaforma di deploy, progetto GCP/billing separato |

---

## 9. Roadmap a fasi

| Fase | Obiettivo | Deliverable | Criterio di uscita | Durata indicativa |
|---|---|---|---|---|
| **0 — Mockup** ✅ | Rendere il progetto tangibile e discutibile | Questo documento + demo end-to-end (`mockup/`) | Decisione go/no-go interna | fatta |
| **1 — Shadow mode** | Provare l'affidabilità a rischio zero | Compilatore v1 (schema contratto reale), motore v1, ledger, riconciliazione notturna su **una gara reale già attiva** (i dati piattaforma si scaricano già oggi) | Riconciliazione verde (100% o divergenze tutte spiegate) per 3 cicli consecutivi + golden test verdi | 6–8 settimane |
| **2 — Backend takeover** | Le gare nuove nascono su REGOLO | Write-back verso PIATTAFORMA (endpoint JSON, fallback browser), control plane operativo (approvazioni, alert), API di serving v1 | 1–2 gare nuove gestite end-to-end: prestazioni, punteggi e credito prodotti da REGOLO, piattaforma solo visualizzazione | 2–3 mesi |
| **3 — Frontend pilota** | Staccare il frontend | Frontend white-label (in casa) su API di serving, per un cliente pilota | Cliente pilota live, NPS/feedback raccolti, zero doppi binari di calcolo | 2–3 mesi (in parallelo a fase 2) |
| **4 — Decommissioning progressivo** | Uscita ordinata dalla PIATTAFORMA | Migrazione cliente per cliente a scadenza gara/contratto | Per ogni cliente migrato: parità funzionale + riconciliazione storica archiviata | continuo |

Decisioni rimandate volutamente a valle della fase 1: scelta DB definitivo (Postgres vs
SQLite/DuckDB evoluti), hosting (lo stack Cloud Run è già rodato), modello LLM del
compilatore (la scelta è incapsulata in L1 e sostituibile).

---

## 10. Rischi e mitigazioni

| Rischio | Probabilità | Mitigazione |
|---|---|---|
| Gli endpoint `/json/*.php` non sono utilizzabili in **scrittura** | Media | Verifica in fase 1 (basso costo); fallback già esistente come pattern: automazione browser dei moduli. In ultima istanza il write-back resta in lettura e la piattaforma viene alimentata coi flussi attuali |
| L'AI interpreta male una clausola | Media | Confidence + escalation umana (clausole dubbie bloccanti), doppio modello sulle gare critiche, golden test per gara, e comunque: **l'interpretazione è approvata da un umano prima di produrre effetti** |
| Errori nel motore di calcolo | Bassa | Shadow mode con riconciliazione vs piattaforma prima di qualunque takeover; golden test automatici; replay per audit |
| PII dell'anagrafica nei prompt | Media | Anonimizzazione sistematica prima di qualunque chiamata LLM; l'anagrafica vera non serve al compilatore (lavora su regole, non su persone) |
| Compliance DPR 430/2001 | Bassa | Il regolamento resta l'unico documento legale; REGOLO ne è l'esecuzione tracciata. L'audit trail clausola→evento *migliora* la difendibilità attuale |
| Doppio binario di calcolo (REGOLO e piattaforma insieme) | Media | Regola fissa: per ogni gara UNA sola fonte di calcolo; la riconciliazione esiste proprio per il transitorio |
| Effort di manutenzione contratti | Bassa | I contratti sono **dati**, non codice: un motore unico serve tutte le gare; le meccaniche nuove estendono lo schema, non la piattaforma |

---

## 11. Governance e compliance

- **Ruoli**: chi compila (AI) ≠ chi approva il contratto (responsabile gara) ≠ chi approva
  i batch credito (operations). Ogni approvazione è registrata con utente e timestamp.
- **GDPR**: anagrafica come master data interno con minimizzazione; PII mai nei prompt;
  diritto all'oblio gestibile a livello ledger (pseudonimizzazione della chiave partecipante).
- **DPR 430/2001**: per ogni gara, il fascicolo di audit (regolamento, versioni contratto,
  report compilazione, run, approvazioni) è generabile in un click.

---

## 12. Il mockup allegato

Per rendere tutto questo concreto, `mockup/` contiene una gara fittizia completa,
ispirata nella struttura a una gara incentive canale **Spazio Enel** (tutti i dati sono
inventati): **"Spazio alla Meta 2026"** — 25 punti vendita in 3 cluster, 6 mesi di gara,
KPI su attivazioni commodity, fibra, fotovoltaico, wallbox e clima.

| Tappa | File | Cosa dimostra |
|---|---|---|
| Il regolamento | `00_regolamento/REGOLAMENTO_SPAZIO_ALLA_META_2026.md` | La fonte: 12 articoli, con 2 clausole volutamente ambigue |
| La compilazione | `01_contratto/compilazione_report.json` | Come lavora L1: clausola per clausola, confidenza, 2 escalation a umano con risoluzione agli atti |
| Il contratto | `01_contratto/gara_spazio_alla_meta.v1.yaml` + `.v2.yaml` | La spec eseguibile; la v2 è la revisione in corso d'opera (cap 600→900, fotovoltaico 150→200 dal 1/6) |
| I dati | `02_dati/*.csv` | Anagrafica, prestazioni aprile/maggio/giugno (parziale), export della piattaforma legacy |
| Il motore | `03_motore/motore.py` | **Vero**: calcola tutto, applica effective dating v1/v2, quarantena un'anomalia, riconcilia con la piattaforma (trova 2 divergenze reali), esegue il what-if retroattivo |
| Il ledger | `output/ledger.jsonl` | Eventi append-only; giugno è `in_approvazione` (HITL) |
| L'API | `04_api/api.py` | Il backend headless su :8788 |
| Frontend utente | http://localhost:8788/ | Cosa vede il punto vendita: saldo, progressi vs target, classifica, catalogo, movimenti trasparenti |
| Backoffice | http://localhost:8788/backoffice | Cosa vede operations: compilazione, riconciliazione, what-if, approvazioni, alert |

### Copione demo (5 minuti)

1. Aprire il **regolamento** e mostrare l'art. 5.7 (storni: "entro 60 giorni" — da quando?).
2. Aprire il **backoffice → Compilazione**: la clausola è stata escalata, risolta col
   promotore, e la risoluzione è agli atti. Le altre 12 sono passate con confidenza alta.
3. Backoffice → **Riconciliazione**: 23 punti vendita allineati, **2 divergenze trovate**
   (uno storno non applicato e un cap sbagliato — della piattaforma). Questo è lo shadow
   mode: la prova di affidabilità prima di migrare alcunché.
4. Backoffice → **What-if**: "se la revisione v2 fosse stata attiva da aprile": delta punti
   per punto vendita e delta budget in euro. Questa è la risposta a "il regolamento è
   cambiato in corso d'opera".
5. Backoffice → **Approvazioni**: il batch di giugno è lì, in attesa di firma. L'AI propone,
   l'umano approva.
6. Aprire il **frontend**: il punto vendita vede saldo, progressi, classifica e ogni
   singolo movimento — trasparenza che oggi non esiste.

---

## 13. KPI di successo del progetto

| KPI | Oggi | Target REGOLO |
|---|---|---|
| Tempo setup nuova gara (regolamento → operativa) | settimane | < 1 settimana |
| Tempo gestione revisione regolamento | settimane / "non fattibile" | < 2 giorni (ricompilazione + replay + approvazione) |
| Change request verso il fornitore piattaforma | continue | → zero per le meccaniche |
| Difendibilità punteggi (clausola→numero) | ricostruzione manuale | audit trail automatico |
| Personalizzazione frontend per cliente | non praticabile | tema/composizione per cliente |
| Errori di calcolo scoperti dai partecipanti | capita | intercettati da riconciliazione e golden test |

---

## 14. Glossario

| Termine | Significato |
|---|---|
| **Contratto di Gara** | La versione strutturata ed eseguibile del regolamento, versionata e approvata |
| **Compilazione** | Il processo AI che trasforma il regolamento in Contratto di Gara |
| **Effective dating** | Ogni versione del contratto vale in una finestra temporale; il motore applica quella giusta |
| **Replay** | Ricalcolo integrale e riproducibile con una data versione del contratto |
| **Ledger** | Registro append-only dei movimenti punti/credito |
| **Shadow mode** | Il motore calcola in parallelo alla piattaforma senza effetti, per confrontare i risultati |
| **Riconciliazione** | Confronto sistematico REGOLO vs PIATTAFORMA con spiegazione delle divergenze |
| **HITL** | Human-in-the-loop: approvazione umana obbligatoria sui passaggi critici |
| **Golden test di gara** | Casi di test (input → punteggio atteso) derivati dal regolamento, eseguiti a ogni modifica |
| **HIE prodotto** | Gerarchia prodotti usata per la valorizzazione dei punti |
| **Strangler** | Strategia di migrazione che svuota progressivamente il sistema legacy invece di sostituirlo di colpo |

---

*REGOLO: in italiano, il regolo è uno strumento di calcolo — deterministico per natura —
e il nome contiene "regola" e "regolamento". Il nome è una proposta: il progetto no.*
