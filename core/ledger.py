"""
REGOLO — L3 LEDGER append-only (decisione 2026-06-11: SQLite → Postgres in scala).

Journal immutabile per partecipante: ogni movimento di punti è un evento che NON
si modifica e NON si cancella (trigger SQL lo impediscono). I saldi non sono un
dato salvato: sono la somma degli eventi. Storni, rettifiche e riaccrediti sono
sempre eventi compensativi, mai UPDATE.

Schema minimale (~1 tabella), WAL mode per letture concorrenti. Payload JSON
versionato (`schema_payload`) dal giorno 1, così l'evoluzione dei campi non rompe
lo storico.

API:
    led = Ledger("gara.db")
    led.append(gara, partecipante, "accredito", 1100, {...})
    led.saldo(gara, partecipante)                 # contabilizzato
    led.saldi(gara)                               # tutti i partecipanti
    led.movimenti(gara, partecipante)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA_PAYLOAD = 1  # versione del formato payload — incrementare se cambiano i campi

TIPI_VALIDI = {"accredito", "storno", "bonus", "rettifica", "premio_classifica",
               "riaccredito", "spesa"}
STATI_VALIDI = {"in_approvazione", "contabilizzato", "annullato"}

_DDL = """
CREATE TABLE IF NOT EXISTS eventi (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    gara_id       TEXT    NOT NULL,
    partecipante  TEXT    NOT NULL,
    seq           INTEGER NOT NULL,           -- progressivo per (gara, partecipante)
    tipo          TEXT    NOT NULL,
    meccanica     TEXT,                        -- regola del contratto che l'ha generato
    punti         INTEGER NOT NULL,            -- può essere negativo (storni/azzeramenti)
    contratto_v   INTEGER,
    periodo       TEXT,                        -- YYYY-MM di competenza
    run_id        TEXT,                        -- esecuzione del motore che l'ha prodotto
    stato         TEXT    NOT NULL DEFAULT 'contabilizzato',
    descrizione   TEXT,
    fonte_clausola TEXT,                        -- tracciabilità → regolamento
    schema_payload INTEGER NOT NULL,
    payload       TEXT    NOT NULL,            -- JSON: tutto il resto, estendibile
    creato_il     TEXT    NOT NULL,
    UNIQUE (gara_id, partecipante, seq)
);
CREATE INDEX IF NOT EXISTS idx_eventi_gara_part ON eventi (gara_id, partecipante);
CREATE INDEX IF NOT EXISTS idx_eventi_run ON eventi (run_id);

-- APPEND-ONLY: nessuno può modificare o cancellare un evento contabilizzato.
CREATE TRIGGER IF NOT EXISTS no_update_eventi
BEFORE UPDATE ON eventi BEGIN
    SELECT RAISE(ABORT, 'ledger append-only: UPDATE vietato (usa un evento di rettifica)');
END;
CREATE TRIGGER IF NOT EXISTS no_delete_eventi
BEFORE DELETE ON eventi BEGIN
    SELECT RAISE(ABORT, 'ledger append-only: DELETE vietato');
END;
"""


class LedgerError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_DDL)
        self._conn.commit()

    # -- scrittura -----------------------------------------------------------

    def append(self, gara_id: str, partecipante: str, tipo: str, punti: int,
               payload: dict | None = None, *, meccanica: str | None = None,
               contratto_v: int | None = None, periodo: str | None = None,
               run_id: str | None = None, stato: str = "contabilizzato",
               descrizione: str | None = None, fonte_clausola: str | None = None,
               creato_il: str) -> int:
        """Aggiunge un evento. `creato_il` è obbligatorio ed esplicito (niente now():
        il determinismo del replay non deve dipendere dall'orologio)."""
        if tipo not in TIPI_VALIDI:
            raise LedgerError(f"tipo evento non valido: {tipo}")
        if stato not in STATI_VALIDI:
            raise LedgerError(f"stato non valido: {stato}")
        cur = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM eventi WHERE gara_id=? AND partecipante=?",
            (gara_id, partecipante))
        seq = cur.fetchone()[0]
        cur = self._conn.execute(
            """INSERT INTO eventi (gara_id, partecipante, seq, tipo, meccanica, punti,
                   contratto_v, periodo, run_id, stato, descrizione, fonte_clausola,
                   schema_payload, payload, creato_il)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (gara_id, partecipante, seq, tipo, meccanica, int(round(punti)),
             contratto_v, periodo, run_id, stato, descrizione, fonte_clausola,
             SCHEMA_PAYLOAD, json.dumps(payload or {}, ensure_ascii=False), creato_il))
        self._conn.commit()
        return cur.lastrowid

    def contabilizza_run(self, run_id: str) -> int:
        """Promuove gli eventi di un run da in_approvazione a contabilizzato (HITL).
        Consentito dal trigger? No: il trigger blocca ogni UPDATE. Per disciplina
        append-only la 'contabilizzazione' è una transizione di stato legittima →
        la realizziamo riscrivendo lo stato SOLO se in_approvazione, via una
        connessione che disabilita temporaneamente il trigger non è pulito.
        Scelta: lo stato si decide all'append. Questo metodo resta come promemoria
        e solleva, per evitare usi impropri."""
        raise LedgerError(
            "Per disciplina append-only lo stato si fissa all'append. La promozione "
            "HITL si modella appendendo gli eventi del run come 'contabilizzato' solo "
            "dopo l'approvazione (vedi motore_gara.esegui).")

    # -- lettura -------------------------------------------------------------

    def saldo(self, gara_id: str, partecipante: str, stato: str = "contabilizzato") -> int:
        cur = self._conn.execute(
            "SELECT COALESCE(SUM(punti),0) FROM eventi WHERE gara_id=? AND partecipante=? AND stato=?",
            (gara_id, partecipante, stato))
        return cur.fetchone()[0]

    def saldi(self, gara_id: str, stato: str = "contabilizzato") -> dict[str, int]:
        cur = self._conn.execute(
            "SELECT partecipante, SUM(punti) s FROM eventi WHERE gara_id=? AND stato=? "
            "GROUP BY partecipante ORDER BY s DESC", (gara_id, stato))
        return {r["partecipante"]: r["s"] for r in cur.fetchall()}

    def movimenti(self, gara_id: str, partecipante: str | None = None) -> list[dict]:
        if partecipante:
            cur = self._conn.execute(
                "SELECT * FROM eventi WHERE gara_id=? AND partecipante=? ORDER BY id",
                (gara_id, partecipante))
        else:
            cur = self._conn.execute("SELECT * FROM eventi WHERE gara_id=? ORDER BY id", (gara_id,))
        out = []
        for r in cur.fetchall():
            d = dict(r)
            d["payload"] = json.loads(d["payload"])
            out.append(d)
        return out

    def conteggio(self, gara_id: str | None = None) -> int:
        if gara_id:
            cur = self._conn.execute("SELECT COUNT(*) FROM eventi WHERE gara_id=?", (gara_id,))
        else:
            cur = self._conn.execute("SELECT COUNT(*) FROM eventi")
        return cur.fetchone()[0]

    def close(self):
        self._conn.close()
