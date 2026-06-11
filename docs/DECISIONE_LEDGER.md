# Decisione L3 — Ledger punti/credito (2026-06-11)

*Chiude la terza e ultima decisione build-vs-buy dei layer core. Fatti verificati su
fonti primarie (GitHub/PyPI/docs ufficiali) l'11/06/2026.*

## Decisione

**Fase 1 (shadow mode): tabella append-only fatta in casa su SQLite (WAL mode).**
**Fase 2+ (produzione multi-gara): stessa tabella, migrata su PostgreSQL (Cloud SQL).**
Adozione di un ledger esterno **solo se** emergeranno requisiti veri di double-entry
(es. budget gara che si decrementa quando il partecipante accredita): in quel caso il
candidato è Formance Ledger.

## Perché

I punti loyalty non sono denaro double-entry: non servono multi-posting atomici tra
conti, serve un **journal immutabile per partecipante**. Lo schema è ~50 righe:

```sql
CREATE TABLE eventi (
  id INTEGER PRIMARY KEY,
  gara_id TEXT NOT NULL,
  partecipante_id TEXT NOT NULL,
  seq INTEGER NOT NULL,             -- progressivo per partecipante
  tipo TEXT NOT NULL,               -- accredito|storno|bonus|rettifica|premio|spesa
  punti INTEGER NOT NULL,
  payload TEXT NOT NULL,            -- JSON: meccanica, contratto_v, run_id, descrizione,
                                    --       event_version (versionato dal giorno 1)
  stato TEXT NOT NULL,              -- in_approvazione|contabilizzato
  creato_il TEXT NOT NULL,
  UNIQUE (gara_id, partecipante_id, seq)   -- optimistic concurrency
);
-- niente UPDATE/DELETE: enforcato con trigger; storni e rettifiche sono
-- SEMPRE eventi compensativi, mai modifiche. Saldo = SUM(punti) filtrato per stato.
```

Disciplina minima (non negoziabile): trigger che blocca UPDATE/DELETE, `event_version`
nel payload, snapshot dei saldi solo come proiezione ricalcolabile.

## I candidati scartati (fatti verificati)

| Candidato | Fatti | Perché no (per ora) |
|---|---|---|
| [Formance Ledger](https://github.com/formancehq/ledger) | **MIT verificata** (core), Go, richiede Postgres, ~1.3k ⭐, sviluppo molto attivo (v2.3.20 dell'11/06/2026), DSL Numscript | Il migliore della categoria, ma è un servizio Go+Postgres da operare per un problema da ~1.000 eventi/giorno. **Piano A per la Fase 2+ se servirà double-entry vero** |
| [Blnk](https://github.com/blnkfinance/blnk) | Apache-2.0, ma richiede Go + Postgres + Redis + Typesense; v0.x, ~446 ⭐ | 4 servizi da gestire, versione 0.x, community piccola: rapporto peso/beneficio peggiore |
| [TigerBeetle](https://github.com/tigerbeetle/tigerbeetle) | Apache-2.0, 16.2k ⭐, client Python ufficiale; i loyalty points sono un caso d'uso documentato | Progettato per milioni di tx/secondo in cluster a 3+ repliche, schema fisso 128 byte senza metadata (descrizioni/payload andrebbero comunque in un DB affiancato): overkill netto |
| [eventsourcing (Python)](https://github.com/pyeventsourcing/eventsourcing) | BSD-3, ~1.7k ⭐, decennale, v9.5.x (2026), SQLite/Postgres nativi, Python 3.10–3.14 | **Piano B** se vorremo aggregati/snapshot pronti restando in Python puro; per "saldo = somma eventi" porta più framework DDD di quanto serva |

Pattern fai-da-te ben documentato: [Event Storage in Postgres](https://dev.to/kspeakman/event-storage-in-postgres-4dk2),
[postgresql-event-sourcing](https://github.com/eugene-khyst/postgresql-event-sourcing) (attenzione
ai sequence gap di Postgres se mai avremo subscriber asincroni),
[sql-event-store](https://github.com/mattbishop/sql-event-store) (schema portabile SQLite/Postgres).

## Trigger di revisione della decisione

- Servono trasferimenti atomici tra conti (budget ↔ partecipanti) → valutare Formance
- Subscriber asincroni sul ledger Postgres → gestire i sequence gap (vedi link) o passare a libreria
- Volumi > ~10⁸ eventi o requisiti di latenza severi → rivalutare la categoria
