# REGOLO — Ricerca: progetti esistenti a cui ispirarsi

*Deep research dell'11/06/2026 — 5 angoli di ricerca in parallelo, 22 fonti primarie,
110 claim estratti, 25 verificati con voto avversariale a 3 (23 confermati, 2 respinti).
Stelle/date sono snapshot dell'11/06/2026.*

---

## La sintesi in tre righe

Non esiste una piattaforma loyalty open-source completa da adottare (Open Loyalty ha
ritirato il codice). Esistono però **componenti embeddabili eccellenti per i singoli
layer** — su tutti **GoRules ZEN Engine** per il motore L2 — e **Catala** è la prova che
"compilare testo legale in codice eseguibile" è un'idea già validata accademicamente:
REGOLO ne è la variante con LLM + escalation umana al posto dell'annotazione manuale.

---

## Tabella per layer

| Layer REGOLO | Progetto | Verdetto | Perché |
|---|---|---|---|
| **L2 Motore** | [GoRules ZEN Engine](https://github.com/gorules/zen) | ✅ **ADOTTARE (valutare con spike)** | MIT, core Rust, ~1.8k ⭐, attivissimo (push 05/2026); `pip install zen-engine` (wheel cp312, in-process, niente server/Java); regole = grafi JSON standard **JDM** → esattamente "regole come dati" |
| **L1 Compilatore** | [Catala](https://github.com/CatalaLang/catala) | 📖 STUDIARE il pattern | Apache-2.0, ~2.3k ⭐, v1.2.0 del 02/06/2026. DSL per algoritmi "faithful-by-construction" da testi legislativi: ogni riga di legge annotata col suo significato eseguibile, revisione dei giuristi. REGOLO = stesso pattern, ma l'annotazione la propone l'LLM con confidenze |
| **L2 Condizioni** | [zeroSteiner/rule-engine](https://github.com/zeroSteiner/rule-engine) | ✅ candidato building block | BSD-3, ~588 ⭐, v5.0.0 05/2026. Expression language Python tipizzato per predicati (`matches/filter/evaluate`): utile per condizioni di eleggibilità come stringhe-dato, se non si usa l'expression language di ZEN |
| **L2 Schema regole** | [json-rules-engine](https://github.com/CacheControl/json-rules-engine) | 📖 STUDIARE lo schema | ISC, ~3.1k ⭐, attivo — ma è JavaScript. Da copiare: condizioni ALL/ANY annidabili ricorsivamente + fact resolution dinamica |
| **L2 Pattern condition→effect** | [Talon.One docs](https://docs.talon.one/docs/product/rules/overview) + [Talang](https://github.com/talon-one/talang) | 📖 STUDIARE il pattern | Ogni regola di campagna = condizioni che attivano effetti. Talang (MIT, Go): DSL JSON-friendly con vincoli di safety (no ricorsione, no loop infiniti) — ma dormiente (31 ⭐, ultimo push 2023) e non embeddabile da Python |
| **L3/L4/L5 validazione** | [Open Loyalty (docs architettura)](https://docs.openloyalty.io/en/latest/developer/architecture/overview.html) | 📖 STUDIARE / ❌ ignorare come codice | Il repo `open-loyalty-framework` è **sparito da GitHub** (404; restano solo mirror abbandonati senza licenza). Ma i docs confermano le nostre scelte: event sourcing (Broadway) proprio per "transactions, points and customer data changes", API headless, cockpit sostituibili |
| L2 alternativa | venmo/business-rules | ❌ non adottare (solo studio/fork) | Python, MIT, ~988 ⭐ ma abbandonato (ultima release 2022, 30 issue senza triage). Attenzione: il claim "configurabile senza deploy di codice" è stato **respinto** in verifica — variables e actions richiedono comunque Python |
| L2 alternativa | pyDMNrules | ❌ IGNORARE | Regole solo in cartelle Excel, fermo dal 2023; il claim "licenza GPLv3" è stato respinto in verifica (licenza da accertare, ma non serve: scartato comunque) |

---

## I due insight architetturali

### 1. Il Contratto di Gara può compilare in JDM (ZEN Engine)

ZEN esegue *decision model* JSON (standard JDM) in-process da Python. Per REGOLO apre
un'opzione a due stadi:

```
regolamento → [L1 Compilatore AI] → Contratto di Gara YAML (artefatto APPROVATO dall'umano)
                                          → [transpiler deterministico] → JDM JSON → ZEN Engine
```

Il contratto resta il nostro schema leggibile/approvabile con `fonte_clausola`; il motore
non lo reimplementiamo da zero ma lo deleghiamo a un engine MIT mantenuto da altri.
**Caveat verificato**: il determinismo di ZEN è inferito, non garantito dai docs — regole
che usano `date/now` lo romperebbero. Il nostro principio (data di riferimento sempre come
input, mai `now()`) va imposto anche sul JDM generato. Effective dating e replay restano
nostri (versioni di file JDM gestite dal control plane).

### 2. Catala valida il concetto di REGOLO

Un progetto accademico maturo (INRIA) esiste proprio per "derivare algoritmi fedeli per
costruzione da testi legislativi", con tracciabilità norma→codice e *default logic* per le
eccezioni. Differenza: lì annota un umano, da noi propone l'LLM e l'umano verifica.
Da studiare del loro approccio: la struttura testo-annotato (il nostro `fonte_clausola` è
la stessa idea), la gestione delle eccezioni, il ruolo di certificazione del giurista.

---

## Aree raccolte ma NON ancora verificate (prossimo approfondimento)

Le fonti sono state lette dagli agenti ma i relativi claim non sono passati dalla verifica
avversariale (budget): trattare come **lead promettenti, da verificare prima di decidere**.

| Area | Lead | Nota |
|---|---|---|
| L3 Ledger | [Formance Ledger](https://github.com/formancehq/ledger), [Blnk](https://github.com/blnkfinance/blnk), [eventsourcing (Python)](https://github.com/pyeventsourcing/eventsourcing) | double-entry ledger pronti vs libreria event sourcing Python; verificare licenze, idoneità a punti (non solo denaro), storni/replay |
| L1 Estrazione LLM | [instructor](https://github.com/567-labs/instructor), [outlines](https://github.com/dottxt-ai/outlines), [LangExtract (Google)](https://github.com/google/langextract) | structured output con retry/validazione Pydantic (instructor è il candidato naturale sopra il nostro compilatore); pattern confidence/HITL |
| L1/L2 Rules-as-code | [OpenFisca](https://github.com/openfisca), [PolicyEngine](https://github.com/PolicyEngine/policyengine-core) | motori Python per legislazione fiscale/welfare con **parametri versionati nel tempo** (effective dating!) — fonte raccolta, claim non verificati |
| Area 6/7 | commission engines, bitemporal data, reconciliation engines | non coperte dalla ricerca: da rifare in un secondo giro |

### Domande aperte (dal report)

1. Quale ledger per L3 (Formance/Blnk/TigerBeetle/eventsourcing)? Nessuno verificato.
2. Quali pattern concreti di confidence+escalation HITL da instructor/outlines/LangExtract?
3. ZEN/JDM supporta nativamente effective dating e replay, o li gestiamo noi come
   versioni dei file JDM nel control plane? (Probabile la seconda.)
4. Esistono commission engine open-source con cap/accelerator/clawback riusabili?

---

## Azioni proposte (recepite in ROADMAP Blocco 1.3)

1. **Spike ZEN Engine** (1 giorno): transpilare il contratto SAM2026 in JDM ed eseguirlo
   con `zen-engine`, confrontando i risultati col nostro motore (392 eventi → devono
   tornare identici). Se regge: L2 = ZEN + nostro layer di effective dating/replay.
2. **Spike instructor** nel compilatore L1 (mezza giornata): structured output con schema
   Pydantic + retry automatico al posto del parsing JSON manuale.
3. Secondo giro di ricerca mirato su L3 (ledger) quando si avvicina la Fase 1.
4. Leggere il paper di Catala (arxiv 2103.03198) prima di scrivere lo schema contratto v1.
