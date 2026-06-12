#!/usr/bin/env python3
"""Test del backbone Fase 1: motore parametrico (fasce) + ledger append-only.
Eseguire: venv/bin/python tests/test_fase1.py — exit 0 = tutto verde."""

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "core"))
import motore_gara  # noqa: E402
from ledger import Ledger, LedgerError  # noqa: E402

# contratto minimale che esercita i tipi di meccanica del pilota
CONTRATTO = {
    "meta": {"gara": "TEST", "contratto_versione": 1,
             "valido_dal": "2026-01-01", "valido_al": "2026-12-31"},
    "meccaniche": [
        {"id": "power_switch", "tipo": "punti_a_fasce", "fonte_clausola": "art.X", "fasce": [
            {"da": 25, "a": 50, "etichetta": "25<kW<=50", "punti": 1100},
            {"da": 50, "a": 100, "etichetta": "50<kW<=100", "punti": 2400},
            {"da": 200, "etichetta": "kW>200", "punti": 8000}]},
        {"id": "gas_switch", "tipo": "punti_a_fasce", "fonte_clausola": "art.X", "fasce": [
            {"etichetta": "G10<CC<=G16", "punti": 1500},
            {"etichetta": "CC>G40", "punti": 5900}]},
        {"id": "power_bweb", "tipo": "punti_per_unita", "punti": 120, "fonte_clausola": "art.X"},
        {"id": "storno_x", "tipo": "storno", "fonte_clausola": "art.Y"},
        {"id": "riaccredito_x", "tipo": "riaccredito", "fonte_clausola": "art.Y"},
    ],
}

falliti = 0
def check(nome, cond):
    global falliti
    print(("  ✓ " if cond else "  ✗ ") + nome)
    if not cond:
        falliti += 1


print("MOTORE — selezione fasce e punti")
m_pow = motore_gara.trova_meccanica(CONTRATTO, "power_switch")
check("30 kW → fascia 25-50 = 1100", motore_gara.punti_per_attivazione(m_pow, grandezza=30)[0] == 1100)
check("50 kW → fascia 25-50 (a inclusivo) = 1100", motore_gara.punti_per_attivazione(m_pow, grandezza=50)[0] == 1100)
check("75 kW → fascia 50-100 = 2400", motore_gara.punti_per_attivazione(m_pow, grandezza=75)[0] == 2400)
check("300 kW → fascia >200 = 8000", motore_gara.punti_per_attivazione(m_pow, grandezza=300)[0] == 8000)
try:
    motore_gara.punti_per_attivazione(m_pow, grandezza=18)  # <=25: nessuna fascia
    check("18 kW → solleva (fuori fascia)", False)
except ValueError:
    check("18 kW → solleva (fuori fascia, niente punti inventati)", True)
m_gas = motore_gara.trova_meccanica(CONTRATTO, "gas_switch")
check("gas G10<CC<=G16 → 1500", motore_gara.punti_per_attivazione(m_gas, fascia="G10<CC<=G16")[0] == 1500)
m_bweb = motore_gara.trova_meccanica(CONTRATTO, "power_bweb")
check("power_bweb → 120", motore_gara.punti_per_attivazione(m_bweb)[0] == 120)

print("\nMOTORE — feed con storno/riaccredito")
feed = [
    dict(_i=1, tipo="attivazione", partecipante="A", data="2026-02-10", kpi="power_switch", grandezza=75),
    dict(_i=2, tipo="attivazione", partecipante="A", data="2026-03-10", kpi="power_bweb"),
    dict(_i=3, tipo="cessazione", partecipante="A", data="2026-03-20"),
    dict(_i=4, tipo="riattivazione", partecipante="A", data="2026-04-05"),
    dict(_i=5, tipo="attivazione", partecipante="B", data="2026-02-15", kpi="gas_switch", fascia="CC>G40"),
]
with tempfile.TemporaryDirectory() as d:
    led = Ledger(Path(d) / "t.db")
    motore_gara.esegui([CONTRATTO], feed, led, gara_id="G", run_id="r1")
    # A: +2400 +120 -2520 (cessazione) +2520 (riaccredito) = 2520
    check("A saldo dopo storno+riaccredito = 2520", led.saldo("G", "A") == 2520)
    check("B saldo = 5900", led.saldo("G", "B") == 5900)
    check("eventi A = 4 (accr, accr, storno, riaccr)", len(led.movimenti("G", "A")) == 4)
    led.close()

print("\nLEDGER — append-only (i trigger devono bloccare)")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "t.db"
    led = Ledger(p)
    eid = led.append("G", "A", "accredito", 100, creato_il="2026-02-01T00:00:00")
    check("append + saldo = 100", led.saldo("G", "A") == 100)
    raw = sqlite3.connect(p)
    try:
        raw.execute("UPDATE eventi SET punti=999 WHERE id=?", (eid,)); raw.commit()
        check("UPDATE bloccato dal trigger", False)
    except sqlite3.Error:
        check("UPDATE bloccato dal trigger", True)
    try:
        raw.execute("DELETE FROM eventi WHERE id=?", (eid,)); raw.commit()
        check("DELETE bloccato dal trigger", False)
    except sqlite3.Error:
        check("DELETE bloccato dal trigger", True)
    raw.close()
    try:
        led.append("G", "A", "tipo_inventato", 1, creato_il="2026-02-01T00:00:00")
        check("tipo evento non valido → solleva", False)
    except LedgerError:
        check("tipo evento non valido → solleva", True)
    led.close()

print(f"\n{'✓ TUTTI VERDI' if not falliti else f'✗ {falliti} FALLITI'}")
sys.exit(1 if falliti else 0)
