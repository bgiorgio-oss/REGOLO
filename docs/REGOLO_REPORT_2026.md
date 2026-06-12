# REGOLO

## Regolamento Eseguibile — Piattaforma Loyalty di Nuova Generazione

### H&A Motivation Company — Report Tecnico e Strategico

**Versione 1.0 | 12 giugno 2026**

---

> **In una frase.** Il regolamento di gara smette di essere un documento che gli umani
> interpretano a mano per configurare una piattaforma rigida, e diventa *codice sorgente*:
> l'AI lo compila in un contratto eseguibile, un motore deterministico lo esegue, un'API
> headless alimenta qualunque frontend. Vincolo non negoziabile: **l'AI scrive le regole,
> una macchina deterministica le applica — mai l'AI a calcolare punti o credito a runtime.**

**Stato del progetto al 12 giugno 2026:**

| Componente | Stato |
|---|---|
| Mockup end-to-end (gara fittizia) | ✅ Operativo — `./run_demo.sh`, porta 8788 |
| Compilatore L1 (regolamento → contratto, AI reale) | ✅ Funzionante — Gemini 2.5 Flash via Vertex + instructor |
| Motore L2 (calcolo deterministico) | ✅ Validato — equivalenza 392/392 con GoRules ZEN Engine |
| Ledger L3 (eventi append-only) | ✅ Deciso (SQLite) — da implementare sul pilota reale |
| API L4 + Frontend L5 + Backoffice L6 | ✅ Demo con azioni reali (ordini, ticket, approvazioni, upload) |
| Decisioni build-vs-buy | ✅ 3/3 chiuse con spike misurati (ZEN, instructor, ledger) |
| Gara pilota Fase 1 | ✅ Scelta e compilata (Enel Energy Rewards B2B 1° sem. 2026) |
| Infrastruttura GCP dedicata | ✅ Progetto `regolo-loyalty-hma` operativo |
| Shadow mode su gara reale | 🔄 In avvio — target: conguaglio finale 30 giugno 2026 |
| Repository | ✅ `github.com/bgiorgio-oss/REGOLO` (privato) |

---

## 1. Executive Summary

REGOLO è il progetto che disaccoppia il frontend dal backend della piattaforma loyalty di
H&A e introduce l'intelligenza artificiale **a compile-time** nella produzione di tutti i
dati di gara: punteggi, credito, anagrafica, classifiche.

Il problema che risolve è strutturale. Oggi ogni gara nasce da un regolamento, ma la
traduzione del regolamento in configurazione di piattaforma è manuale, rigida e fragile:
quando il regolamento cambia in corso d'opera — e cambia quasi sempre — le implementazioni
necessarie possono essere troppe, troppo lente, o semplicemente non fattibili dal fornitore
della piattaforma attuale. Inoltre frontend (esperienza dell'utente finale) e backend
(meccaniche di calcolo) sono inscindibili: non si può personalizzare l'uno senza toccare
l'altro.

La soluzione si articola su tre mosse e sei layer:

1. **Il regolamento diventa eseguibile.** Un compilatore AI legge il documento e produce il
   *Contratto di Gara*: una specifica strutturata, versionata e approvata da un umano, in cui
   ogni regola cita la clausola di origine.
2. **Il calcolo esce dalla piattaforma.** Un motore deterministico (zero AI a runtime)
   applica il contratto ai dati di prestazione e produce punteggi e credito come eventi su un
   ledger append-only. Una revisione di regolamento diventa: nuova versione del contratto →
   replay → diff visibile → conguagli espliciti.
3. **Il frontend si stacca.** Un'API di serving espone saldi, classifiche, progressi e
   cataloghi a qualunque interfaccia: il nuovo frontend white-label sviluppato in casa e,
   nel transitorio, la piattaforma esistente alimentata coi dati già calcolati.

A differenza di un progetto su carta, REGOLO al 12 giugno 2026 ha già: un **mockup
funzionante end-to-end** di una gara completa; un **compilatore reale** che ha digerito un
regolamento Enel vero; le **tre decisioni tecnologiche fondanti già prese e misurate** con
spike di codice; e la **Fase 1 avviata** su una gara reale in corso. Il rischio tecnologico
del progetto è quindi basso: i pezzi non sono ipotesi, sono già stati provati.

### Numeri chiave al 12 giugno 2026

| Metrica | Valore |
|---|---|
| Layer architetturali progettati | 6 (Compilatore, Motore, Ledger, API, Frontend, Control plane) |
| Mockup — gara fittizia "Spazio alla Meta 2026" | 25 punti vendita, 3 cluster, 6 mesi, 392 eventi a ledger |
| Spike motore ZEN — equivalenza col motore proprio | **392/392 celle identiche**, 0,53 ms/valutazione |
| Spike compilatore — parametri estratti vs contratto approvato | **17/17 conformi**, escalation di ambiguità preservata |
| Golden test di gara (doppio motore Python + ZEN) | **17/17 verdi** su entrambi |
| Compilazione regolamento reale (pilota Enel B2B) | ~70 s, ~8.000 token in / ~5.000 out, 8–9 escalation |
| Decisioni build-vs-buy chiuse con spike | 3/3 (motore, compilatore, ledger) |
| Costo AI per compilazione di un regolamento | ordine dei centesimi (Gemini 2.5 Flash) |
| Discrepanze reali già intercettate sul pilota | 1 critica (date di eleggibilità contratti) |
| Commit / stato repo | ~12 commit su `github.com/bgiorgio-oss/REGOLO` (privato) |

Il progetto è alla soglia della prima validazione sul campo: lo *shadow mode* sul conguaglio
finale della gara pilota (30 giugno 2026).

---

## 2. Contesto: il reparto Loyalty e la piattaforma attuale

H&A Motivation Company gestisce programmi di loyalty e incentivazione commerciale per grandi
clienti (Enel tra i principali). Lo strumento centrale del reparto Loyalty — che in questo
documento chiamiamo "la PIATTAFORMA" — gestisce oggi in un unico blocco:

- **lato frontend (utente finale):** visualizzazione delle performance, comunicazioni,
  caricamento e spesa del credito, cataloghi premi, contact center;
- **lato backend (operations):** creazione di gare e concorsi, HIE prodotto (valorizzazione
  dei punti), anagrafica, gestione cluster, caricamento dati di prestazione, caricamento del
  credito.

### I tre dolori strutturali

| Dolore | Conseguenza |
|---|---|
| **Rigidità alle variazioni** | La piattaforma è strutturata a inizio progetto sulla definizione iniziale delle operazioni. Ogni variazione in corso d'opera è un'implementazione: lenta, costosa, a volte dichiarata non fattibile dal fornitore |
| **Accoppiamento frontend/backend** | Impossibile personalizzare l'esperienza di un cliente senza toccare le meccaniche di calcolo, e viceversa |
| **Scollamento dal regolamento** | Il documento che definisce legalmente la gara viene interpretato a mano e trascritto in configurazioni: nessun legame verificabile tra clausola e numero mostrato all'utente |

### Il vincolo di contesto

Le manifestazioni a premio in Italia sono materia regolata (DPR 26 ottobre 2001, n. 430). Il
regolamento ha valore legale e i punteggi devono essere difendibili in caso di contestazione.
Qualunque soluzione deve quindi **aumentare** l'auditabilità, non ridurla — ed è esattamente
ciò che fa la tracciabilità clausola → regola → evento → saldo di REGOLO.

### Rapporto con i progetti esistenti (ARGO/MAGI)

REGOLO è un progetto **nuovo e isolato**. Non condivide codice, virtual environment, database,
porte o credenziali con AUTOMAZIONI (la piattaforma operativa ARGO e il sistema AI MAGI).
I pattern già validati in quei progetti — interrupt e approvazione umana, generazione di
logica eseguibile, golden test di regressione, anonimizzazione PII — vengono **reimplementati**
in REGOLO, mai importati. MAGI viene usato esclusivamente come *servizio* (interrogazione
HTTP della knowledge base aziendale) per ritrovare documenti — il che non viola l'isolamento,
perché non c'è condivisione di codice. Questa scelta protegge entrambi i progetti: REGOLO non
può rompere la produzione di ARGO, e ha un ciclo di vita completamente indipendente.

---

## 3. Il principio cardine: compilare, non calcolare

Prima dell'architettura, la decisione da cui dipende tutto il resto. Ci sono due modi di
"mettere l'AI nella produzione dei dati":

**A) AI a runtime** — chiedere al modello, a ogni caricamento, "calcola i punti di questi
5.000 partecipanti secondo il regolamento". **Non si fa, mai.** Non è deterministico (stessa
domanda, risposte diverse), non è auditabile, non scala, e in un contesto regolato (DPR
430/2001) sarebbe indifendibile: se un partecipante contesta un punteggio bisogna poter
dimostrare *esattamente* come è stato calcolato.

**B) AI a compile-time** — l'AI legge il regolamento *una volta* (e a ogni revisione) e
produce un artefatto strutturato e versionato, il **Contratto di Gara**. Un umano lo approva.
Da quel momento un motore deterministico esegue quelle regole su qualunque dato, sempre uguale,
sempre tracciabile.

REGOLO adotta integralmente l'approccio B. La conseguenza non è solo tecnica ma anche
economica: l'LLM si paga alla compilazione e alle revisioni, non a ogni transazione — ordine
dei centesimi per gara, non per partecipante.

---

## 4. Architettura a sei layer

```
            REGOLAMENTO.docx / .pdf  (fonte di verità, versionata)
                    │
        ┌───────────▼───────────┐
   L1   │ COMPILATORE (AI+HITL) │  estrazione + structured output + confidenze
        │ regolamento → contratto│  + escalation umana delle ambiguità
        └───────────┬───────────┘
                    │ Contratto di Gara v1, v2, … (YAML, effective dating)
        ┌───────────▼───────────┐
   L2   │ MOTORE DETERMINISTICO │  applica formule, cap, bonus, storni, classifiche.
        │  (GoRules ZEN + layer) │  Zero LLM. Replay-abile. Quarantena anomalie.
        └───────────┬───────────┘
                    │ eventi
        ┌───────────▼───────────┐
   L3   │ LEDGER (append-only)  │  ogni movimento = evento immutabile con riferimento
        │ punti & credito (SQLite)│ a regola, versione contratto, run, stato
        └───────────┬───────────┘
                    │
        ┌───────────▼───────────┐      ┌──────────────────────────┐
   L4   │ API DI SERVING        │◄─────│ L6 CONTROL PLANE         │
        │ (FastAPI, headless)    │      │ approvazioni HITL,        │
        └───────┬───────┬───────┘      │ riconciliazione, what-if, │
                │       │              │ alert qualità dati        │
        ┌───────▼──┐ ┌──▼────────────┐ └──────────────────────────┘
   L5   │ FRONTEND │ │ PIATTAFORMA    │
        │ headless │ │ legacy (transit)│
        └──────────┘ └────────────────┘
```

### Stack tecnologico

| Componente | Tecnologia | Stato |
|---|---|---|
| Linguaggio | Python 3.12 — venv locale `venv/` (isolato) | Operativo |
| Compilatore L1 | Gemini 2.5 Flash via Vertex AI (ADC) + `instructor` + schema Pydantic | Operativo |
| Estrazione documenti | `pypdf`, `python-docx` (regolamenti PDF/DOCX, tabelle incluse) | Operativo |
| Motore L2 | GoRules **ZEN Engine** (core Rust, JDM JSON, `pip install zen-engine`) + layer proprio | Validato su spike |
| Ledger L3 | Tabella append-only SQLite (WAL) → PostgreSQL in scala | Deciso, da implementare |
| API L4 | FastAPI + Uvicorn — porta 8788 | Operativo (demo) |
| Frontend L5 / Backoffice L6 | HTML/CSS/JS (demo) → frontend white-label interno (Fase 3) | Demo con azioni reali |
| Infrastruttura | Google Cloud (progetto dedicato `regolo-loyalty-hma`): Vertex, Cloud Run, Secret Manager | Progetto creato |
| Versionamento | Git — `github.com/bgiorgio-oss/REGOLO` (privato) | Attivo |

### I sette principi non negoziabili

1. **AI a compile-time, mai a runtime.** L'LLM produce il contratto; i punti li calcola solo
   il motore deterministico.
2. **Determinismo e replay.** Ogni run registra versione contratto + hash input + output:
   qualunque numero è riproducibile a distanza di anni.
3. **Ledger append-only.** Il credito è denaro: mai sovrascritto, solo movimentato (accredito,
   storno, rettifica, spesa). I saldi sono somme di eventi.
4. **Human-in-the-loop sui soldi.** Nessun batch di credito viene contabilizzato senza
   approvazione esplicita. L'AI propone, un umano firma.
5. **Tracciabilità clausola → numero.** Documento → regola → evento → saldo: catena completa
   e ispezionabile, anche in caso di contestazione.
6. **Isolamento dai progetti esistenti.** Ambiente nuovo; i pattern si reimplementano, mai si
   importano.
7. **Strangler, mai big-bang.** La piattaforma legacy si svuota una funzione alla volta, ogni
   passo reversibile e misurato.

---

## 5. L1 — Il Compilatore di Regolamenti

È il cuore differenziante di REGOLO: ciò che non esiste in nessun prodotto sul mercato.

**Cosa fa.** Prende un regolamento (PDF, DOCX, testo) e produce due artefatti: il *Contratto
di Gara* (YAML strutturato ed eseguibile) e un *report di compilazione* (clausola per clausola:
testo estratto, interpretazione, confidenza 0–1, stato). Ogni regola del contratto cita
l'articolo di origine nel campo `fonte_clausola`.

**Come è costruito.** La struttura del contratto non vive nel prompt ma in uno **schema
Pydantic** (`schema_contratto.py`) con validatori di business: confidenza nel range valido,
coerenza fra checklist delle ambiguità ed escalation, date in formato ISO. La chiamata al
modello passa per **instructor**, che valida l'output contro lo schema e ritenta
automaticamente in caso di errore.

**La scelta di instructor (non il constrained decoding nativo).** Uno spike misurato
(2026-06-11) ha confrontato le due strade a parità di prompt e modello. Entrambe estraevano
correttamente i 17/17 parametri numerici, ma con il constrained decoding nativo di Gemini il
modello diventa "compilativo" e **smette di segnalare le ambiguità** (zero escalation su due
run, anche con la checklist resa obbligatoria). Con instructor il comportamento riflessivo si
preserva e le clausole ambigue vengono escalate. Per REGOLO la capacità di dire "non sono
sicuro" vale più della garanzia sintattica: è il cuore del gate human-in-the-loop.

**La checklist delle ambiguità.** Il prompt impone al modello cinque controlli espliciti:
decorrenze delle finestre temporali, ricorrenza dei bonus, cap lordo/netto, definizione delle
grandezze, termini vaghi con effetti sul calcolo. Un'interpretazione "ragionevole ma non
scritta nel regolamento" è trattata come un errore, non come un servizio: va in stato
`da_verificare` e blocca, finché un umano non la scioglie.

**Prova sul campo.** Sul regolamento reale "Enel Energy Rewards – Agenzie B2B – 1° sem. 2026"
(8 pagine, ~22.000 caratteri) il compilatore ha prodotto in ~70 secondi un contratto con la
tabella punti per fasce di potenza (kW) e classe gas estratta correttamente, ha lasciato
vuote le sezioni non previste dal regolamento (niente cluster, niente classifica — senza
inventarle), e ha sollevato 8–9 escalation di qualità, fra cui l'autodenuncia di aver
*inferito* un tasso €/punto non presente nel testo (confidenza 0,1) e il rilievo che il
"segmento SME" e le classi gas non sono definiti nel regolamento.

---

## 6. L2 — Il Motore Deterministico

**Cosa fa.** Applica il Contratto di Gara ai dati di prestazione e produce gli eventi: punti
per unità, punti a fasce/scaglioni, cap mensili, moltiplicatori temporali, bonus condizionali,
storni, classifiche per cluster. Gestisce l'**effective dating** (ogni versione del contratto
vale in una finestra temporale; il motore applica la versione giusta per ciascun periodo) e il
**replay** (ricalcolo integrale con qualunque versione, per what-if, conguagli e audit). Gli
input anomali (valori fuori scala rispetto allo storico) vengono messi in **quarantena**:
esclusi dal calcolo e segnalati, non calcolati.

**La decisione build-vs-buy.** Inizialmente il motore era scritto a mano (e funziona: è il
motore Python del mockup). Uno spike (2026-06-11) ha verificato se valesse la pena delegarlo a
**GoRules ZEN Engine** — un rules engine open source con licenza MIT, core in Rust,
installabile da Python con una riga, che esegue "regole come dati" in formato JSON (standard
JDM). Il test: transpilare il Contratto di Gara in JDM, eseguirlo con ZEN e confrontare ogni
singola cella con il ledger del motore proprio.

**Risultato: 392 celle su 392 identiche, zero divergenze, 0,53 ms a valutazione.** Cap,
acceleratori temporali, bonus condizionali, storni: tutto riproducibile in ZEN. Decisione:
in produzione il motore L2 sarà ZEN per le formule + un layer proprio per ciò che ZEN non
copre (effective dating, replay, quarantena, classifiche multi-partecipante, ledger). Il
motore Python resta come *secondo motore indipendente* per il doppio controllo.

**Determinismo.** Caveat verificato: il determinismo di ZEN non è garantito se le regole usano
funzioni temporali (`now`). REGOLO impone che la data di riferimento sia sempre un input
esplicito, mai letta dall'orologio — vincolo che si applica anche al JDM generato.

---

## 7. L3 — Il Ledger

**Cosa fa.** Registra ogni movimento di punti/credito come evento immutabile: accredito,
storno, bonus, rettifica, premio di classifica, spesa a catalogo. Ogni evento porta gara,
partecipante, periodo, meccanica, punti, versione del contratto, identificativo del run e
stato (`in_approvazione` → `contabilizzato`). I saldi non esistono come dato salvato: sono
viste calcolate come somma degli eventi. Una revisione retroattiva non riscrive nulla — genera
eventi di rettifica espliciti.

**La decisione build-vs-buy.** Una ricerca con fonti verificate (2026-06-11) ha confrontato i
candidati: Formance Ledger (MIT, ottimo ma è un servizio Go+Postgres da operare), Blnk
(richiede 4 servizi), TigerBeetle (overkill: progettato per milioni di transazioni al secondo
in cluster), la libreria Python `eventsourcing` (matura ma porta un intero framework DDD).
**Decisione per la Fase 1: tabella append-only fatta in casa su SQLite** (WAL mode, trigger
anti-UPDATE/DELETE, storni come eventi compensativi, payload versionato). I punti loyalty non
sono denaro double-entry: serve un journal immutabile per partecipante, non un motore
contabile. Lo schema è ~50 righe. In Fase 2+ la stessa tabella migra su PostgreSQL (Cloud SQL);
Formance resta il piano A solo se emergeranno requisiti veri di double-entry tra conti.

---

## 8. L4/L5/L6 — API, Frontend e Control Plane

**L4 — API di serving (il backend headless).** FastAPI sulla porta 8788. È l'unica porta di
accesso ai dati per *tutti* i consumatori: il nuovo frontend, la piattaforma legacy, una DEM,
un export. Espone saldi, movimenti, progressi, classifiche, cataloghi, comunicazioni in
lettura; e azioni in scrittura (ordini, ticket, approvazioni, upload).

**L5 — Frontend punto vendita.** Nel mockup è una single-page application con sei sezioni:
dashboard (saldo, progressi vs target, classifica), catalogo con richiesta premi (scala il
saldo con controllo disponibilità), storico ordini, movimenti filtrabili con export CSV,
assistenza/contact center (apertura ticket, incluse contestazioni ex art. 9.2, con thread di
risposta), news. In produzione (Fase 3) sarà un frontend white-label sviluppato internamente,
con tema per cliente e widget derivati dal contratto. Lo sviluppo interno del frontend è stato
confermato.

**L6 — Control plane (backoffice operations).** Dodici aree: panoramica, gare con versioni di
contratto, compilazione (con il banner della compilazione AI reale), caricamenti con drag&drop
e validazione (schema, codici, anomalie), riconciliazione, what-if, approvazioni HITL,
anagrafica, contact center, comunicazioni, alert qualità dati, ledger. Le azioni del mockup
sono reali e persistono: l'approvazione di un batch sposta davvero gli eventi a contabilizzato
e aggiorna i saldi che il punto vendita vede sul frontend.

**Nota sul mockup.** La separazione è netta e architetturalmente corretta: ciò che *calcola*
il motore vive in uno store di sola lettura; ciò che *fanno* gli utenti vive in uno store
runtime separato; l'API compone le due viste. Le azioni sono state collaudate end-to-end
(11 azioni su 11 verificate), aritmetica inclusa.

---

## 9. La gara pilota e lo shadow mode

**La scelta del pilota.** Interrogando la knowledge base aziendale (MAGI) sono stati
individuati i regolamenti reali disponibili. Il pilota confermato è **"Enel Energy Rewards –
Agenzie B2B – 1° Semestre 2026"**, gara in corso (1 febbraio → 30 giugno 2026). La scadenza
ravvicinata è un'opportunità: arrivando pronti, lo shadow mode si esegue sul **conguaglio
finale** — il banco di prova più severo possibile.

**Cosa calcola chi.** Il portale visibile alle agenzie è Enel Flow (del cliente), ma **i saldi
e i punti li calcola e gestisce H&A**. Questo semplifica lo shadow mode: REGOLO non si confronta
con una scatola nera del cliente, ma con il **metodo attuale di H&A** (i file di caricamento
punti preparati internamente). Il confronto è sotto il nostro controllo, e la persona che
prepara oggi i caricamenti è anche chi valida i golden test e scioglie le ambiguità di clausola
— un unico punto di contatto, iterazione rapida.

**Il primo risultato concreto.** Già in fase di compilazione, incrociando i documenti della
gara, REGOLO ha intercettato una **discrepanza reale**: il regolamento indica che maturano
punti i contratti "sottoscritti dal 1° gennaio 2026", mentre una comunicazione alle agenzie
dice "dal 19 gennaio 2026". Diciotto giorni di contratti che maturano o no punti a seconda del
documento che fa fede. È esattamente il tipo di errore che REGOLO esiste per scoprire — e lo
ha fatto prima ancora di entrare in produzione.

**Il golden test.** Per la gara pilota si costruiranno 10–15 casi "input → punteggio atteso",
validati a mano, da eseguire a ogni modifica di contratto o motore. È il pattern di
riconciliazione interna già dimostrato sul mockup (17 casi su doppio motore, tutti verdi).

---

## 10. Il mockup: la dimostrazione end-to-end

Per rendere il progetto tangibile prima di toccare dati reali, è stata costruita una gara
fittizia completa, ispirata nella struttura a una gara incentive di canale: **"Spazio alla
Meta 2026"** — 25 punti vendita in 3 cluster (GOLD/SILVER/BRONZE), 6 mesi, KPI su attivazioni
commodity, fibra, fotovoltaico, wallbox e climatizzatori. Si avvia con `./run_demo.sh`.

| Tappa | Cosa dimostra |
|---|---|
| Regolamento fittizio (12 articoli, 2 ambiguità pilotate) | La fonte realistica, con i tranelli dei regolamenti veri |
| Contratto v1 + v2 (effective dating) | La revisione in corso d'opera: cap 600→900, fotovoltaico 150→200 dal 1° giugno |
| Motore deterministico | 392 eventi a ledger, calcolo reale e riproducibile |
| Riconciliazione | 23/25 punti vendita allineati, **2 divergenze trovate e diagnosticate automaticamente** |
| What-if retroattivo | "Se la v2 fosse valsa da aprile": +6.750 punti = +1.687,50 € di budget, replay reale |
| Quarantena | Un flusso anomalo (380 attivazioni vs media ~50) escluso e segnalato |
| HITL | Batch di giugno in coda approvazioni, in attesa di firma |

Le due divergenze della riconciliazione meritano una nota: il motore non solo le ha trovate,
ma le ha **spiegate da solo** — "cap commodity errato ad aprile" e "storni di maggio non
applicati, con conseguente bonus obiettivo non dovuto". L'effetto a cascata (lo storno mancante
che fa scattare un bonus indebito) è stato ricostruito automaticamente: è l'argomento più
convincente dello shadow mode.

---

## 11. Costi

I costi di REGOLO sono di due nature, entrambe contenute.

**Costi AI (LLM).** Solo a compile-time: una compilazione di un regolamento da 8 pagine
consuma circa 8.000 token in input e 5.000 in output su Gemini 2.5 Flash — **ordine dei
centesimi**. Una gara si compila una volta più una manciata di revisioni. Non c'è costo AI per
transazione, per partecipante o per caricamento: il motore deterministico non usa l'LLM.

**Costi infrastruttura.** Progetto GCP dedicato (`regolo-loyalty-hma`), separato da quello di
MAGI anche per il billing. Per la Fase 1 (shadow mode, nodo singolo) il carico è trascurabile:
Cloud Run scala a zero quando non serve, SQLite non ha costi di gestione, il volume di una gara
è dell'ordine di migliaia di partecipanti e milioni di eventi totali — gestibili senza
infrastruttura pesante. Una stima realistica per la Fase 1 è dell'ordine di pochi euro al mese,
più i centesimi delle compilazioni.

---

## 12. Decisioni architetturali prese (con evidenza)

A differenza di un progetto in cui le scelte tecnologiche sono ipotesi da verificare, le tre
decisioni fondanti di REGOLO sono già state chiuse con spike di codice misurati:

| Decisione | Esito | Evidenza |
|---|---|---|
| **Motore L2** | GoRules ZEN Engine (JDM) + layer proprio | Spike: 392/392 celle identiche al motore Python, 0,53 ms/valutazione |
| **Compilatore L1** | Schema Pydantic + instructor (non constrained decoding nativo) | Spike: 17/17 parametri; solo instructor preserva le escalation di ambiguità |
| **Ledger L3** | Tabella append-only SQLite → PostgreSQL | Ricerca con fonti verificate; Formance/Blnk/TigerBeetle scartati con motivazione |
| **Dove gira la Fase 1** | Cloud Run, progetto GCP nuovo e separato | Progetto `regolo-loyalty-hma` creato e operativo |
| **Frontend** | Sviluppo interno | Confermato |
| **Isolamento** | Nessun codice condiviso con ARGO/MAGI | MAGI usato solo come servizio HTTP |

Inoltre, la ricerca di mercato (verifica avversariale, 22 fonti) ha confermato una cosa
importante: **non esiste una piattaforma loyalty open-source completa da adottare** (l'unica
storicamente rilevante, Open Loyalty, ha ritirato il codice), e l'unica architettura
documentata seria conferma le scelte di REGOLO (event sourcing per i punti, API headless,
frontend sostituibili). Il progetto più vicino al nostro compilatore è Catala (un linguaggio
accademico per "compilare" testi legislativi in codice), che però richiede annotazione manuale:
REGOLO ne è la variante con AI + verifica umana. In sintesi, stiamo assemblando componenti
maturi attorno all'unico pezzo davvero nostro e differenziante — il compilatore di regolamenti.

---

## 13. Roadmap a fasi

| Fase | Obiettivo | Criterio di uscita | Stato |
|---|---|---|---|
| **0 — Mockup** | Rendere il progetto tangibile | Decisione go/no-go interna | ✅ Completata |
| **1 — Shadow mode** | Provare l'affidabilità a rischio zero su una gara reale | Riconciliazione verde (o divergenze tutte spiegate) per 3 cicli + golden test verdi | 🔄 Avviata |
| **2 — Backend takeover** | Le gare nuove nascono su REGOLO; la piattaforma riceve i dati già calcolati | 1–2 gare gestite end-to-end | ⬜ Da fare |
| **3 — Frontend pilota** | Staccare il frontend (white-label, in casa) | Cliente pilota live, zero doppi binari di calcolo | ⬜ Da fare |
| **4 — Decommissioning** | Uscita ordinata dalla piattaforma legacy, cliente per cliente | Parità funzionale + audit storico per cliente | ⬜ Da fare |

**Stato della Fase 1 al 12 giugno 2026:** pilota scelto e compilato; infrastruttura GCP pronta;
schema del contratto esteso alle meccaniche reali (fasce, riaccredito); censimento dei dati
fatto. Restano da costruire: il motore parametrico sulle meccaniche del pilota, il ledger
SQLite, il job di riconciliazione, e i golden test della gara. Target naturale: il conguaglio
finale del 30 giugno.

---

## 14. Limiti e rischi

| Rischio | Probabilità | Mitigazione |
|---|---|---|
| Gli endpoint della piattaforma legacy non sono usabili in scrittura (write-back) | Media | Da verificare in Fase 2; fallback con automazione browser; in ultima istanza la piattaforma resta alimentata coi flussi attuali. **Nota**: poiché H&A già calcola i punti, il write-back impatta meno del previsto |
| L'AI interpreta male una clausola | Media | Confidenze + escalation bloccanti + checklist; e comunque l'interpretazione è approvata da un umano prima di produrre effetti. La rilevazione varia tra run → in Fase 1 si usa l'unione di più passaggi/modelli |
| Errori nel motore di calcolo | Bassa | Shadow mode con riconciliazione prima di qualunque takeover; doppio motore indipendente (Python + ZEN); golden test |
| PII dell'anagrafica nei prompt | Media | Anonimizzazione sistematica; il compilatore lavora su regole, non su persone |
| Discrepanze nei documenti di gara | Reale (già osservata) | Il sistema le intercetta (vedi pilota: date 1/1 vs 19/1); restano da sciogliere col cliente prima del calcolo |
| Bus factor / dipendenza da una persona | Media | Codice versionato e documentato su Git; questo report; la roadmap con registro decisioni |
| Maturità del progetto | Media | È a uno stadio iniziale: il mockup è solido, ma il motore reale sul pilota e il ledger sono ancora da implementare. La Fase 1 serve proprio a validare prima di impegnarsi |

---

## 15. Glossario

| Termine | Significato |
|---|---|
| **Contratto di Gara** | Versione strutturata ed eseguibile del regolamento, versionata e approvata |
| **Compilazione** | Processo AI che trasforma il regolamento in Contratto di Gara |
| **Effective dating** | Ogni versione del contratto vale in una finestra temporale; il motore applica quella giusta |
| **Replay** | Ricalcolo integrale e riproducibile con una data versione del contratto |
| **Ledger** | Registro append-only dei movimenti di punti/credito |
| **Shadow mode** | Il motore calcola in parallelo al metodo attuale, senza effetti, per confrontare i risultati |
| **Riconciliazione** | Confronto sistematico REGOLO vs metodo attuale, con spiegazione delle divergenze |
| **HITL** | Human-in-the-loop: approvazione umana obbligatoria sui passaggi critici |
| **Golden test di gara** | Casi di test (input → punteggio atteso) derivati dal regolamento, eseguiti a ogni modifica |
| **JDM** | JSON Decision Model: lo standard di "regole come dati" eseguito da ZEN Engine |
| **HIE prodotto** | Gerarchia prodotti usata per la valorizzazione dei punti |
| **Strangler** | Strategia di migrazione che svuota progressivamente il sistema legacy invece di sostituirlo di colpo |

---

## 16. Conclusioni

REGOLO non è un'idea su carta: al 12 giugno 2026 è un mockup funzionante, tre decisioni
tecnologiche chiuse con prove misurate, e una gara reale già compilata. L'intuizione di fondo —
trattare il regolamento come codice sorgente da compilare, e tenere l'AI rigorosamente a
compile-time — si è dimostrata solida a ogni passo: il motore ZEN riproduce i calcoli al 100%,
il compilatore estrae correttamente un regolamento Enel vero e, soprattutto, sa dire "non sono
sicuro" sulle clausole ambigue invece di inventare. Il valore del progetto è già emerso prima
della produzione: una discrepanza reale tra documenti della gara pilota, intercettata in
automatico.

**Priorità immediate (giugno 2026):**

1. Review umana del contratto compilato del pilota (verifica numeri vs PDF) — in corso.
2. Sciogliere col cliente la discrepanza sulle date di eleggibilità (1/1 vs 19/1).
3. Implementare motore parametrico + ledger SQLite sulla gara pilota.
4. Job di riconciliazione e golden test per arrivare pronti al conguaglio del 30 giugno.

**Direzione a medio termine:** se lo shadow mode è verde, la Fase 2 sposta su REGOLO le gare
nuove (la piattaforma legacy degrada a visualizzazione), e la Fase 3 stacca il frontend con la
prima esperienza white-label sviluppata in casa. Il decommissioning della piattaforma attuale
avviene poi cliente per cliente, a scadenza naturale dei contratti — mai con un big-bang.

Il rischio del progetto non è tecnologico: i pezzi funzionano. È di esecuzione e di adozione —
ed è esattamente ciò che la Fase 1, a rischio zero e su dati reali, serve a misurare prima di
qualunque impegno più grande.

---

*REGOLO — in italiano, il "regolo" è uno strumento di calcolo, deterministico per natura; e il
nome contiene "regola" e "regolamento". Documento generato il 12 giugno 2026. Codice e
documentazione: `github.com/bgiorgio-oss/REGOLO` (privato). Per la versione grafica della
presentazione: «REGOLO - Presentazione Progetto.html/.pdf» (Desktop).*
