#!/usr/bin/env python3
"""
REGOLO — Orchestratore Fase 1 sul pilota Enel Energy Rewards B2B.

Mette in fila i tre layer reali: Contratto (L1, già compilato) → Motore (L2) →
Ledger (L3). Finché Giorgio non fornisce i file di caricamento reali, gira su un
feed SINTETICO ma realistico (agenzie che attivano contratti power/gas/bweb/rid,
con alcune cessazioni e riattivazioni per esercitare storni e riaccrediti).
Quando arriveranno i dati veri, si sostituisce solo `genera_feed_sintetico` con
un loader del tracciato reale: motore e ledger restano identici.

Uso:
  venv/bin/python core/esegui_pilota.py
  venv/bin/python core/esegui_pilota.py --verifica-determinismo
"""

import argparse
import random
import sys
from pathlib import Path

import yaml

QUI = Path(__file__).parent
ROOT = QUI.parent
sys.path.insert(0, str(QUI))
from ledger import Ledger  # noqa: E402
import motore_gara  # noqa: E402

GARA_DIR = ROOT / "gare" / "energy_rewards_b2b_2026_s1"
CONTRATTO = GARA_DIR / "compilato" / "gara_compilata_ai.yaml"
DB = GARA_DIR / "pilota.db"
GARA_ID = "energy_rewards_b2b_2026_s1"

# 12 agenzie fittizie (codici e nomi inventati)
AGENZIE = [f"AG-{n:03d}" for n in range(1, 13)]
GAS_FASCE = ["G10<CC<=G16", "G16<CC<=G40", "CC>G40"]
KW_TAGLIE = [18, 30, 30, 45, 75, 90, 120, 150, 250, 350]  # 18 < 25 → niente punti (atteso)
MESI = ["2026-02", "2026-03", "2026-04", "2026-05"]


def genera_feed_sintetico(seed: int = 2026) -> list[dict]:
    """Feed cronologico FITTIZIO (deterministico col seed). Da sostituire col loader
    del tracciato reale quando arrivano i caricamenti di Giorgio."""
    rng = random.Random(seed)
    feed, i = [], 0
    for mese in MESI:
        for ag in AGENZIE:
            for _ in range(rng.randint(2, 8)):  # contratti attivati nel mese
                i += 1
                g = rng.randint(1, 100)
                if g <= 45:    # power switch
                    feed.append(dict(_i=i, tipo="attivazione", partecipante=ag,
                                     data=f"{mese}-{rng.randint(1,28):02d}",
                                     kpi="power_switch", grandezza=rng.choice(KW_TAGLIE)))
                elif g <= 70:  # gas switch
                    feed.append(dict(_i=i, tipo="attivazione", partecipante=ag,
                                     data=f"{mese}-{rng.randint(1,28):02d}",
                                     kpi="gas_switch", fascia=rng.choice(GAS_FASCE)))
                elif g <= 80:
                    feed.append(dict(_i=i, tipo="attivazione", partecipante=ag,
                                     data=f"{mese}-{rng.randint(1,28):02d}", kpi="power_bweb"))
                elif g <= 88:
                    feed.append(dict(_i=i, tipo="attivazione", partecipante=ag,
                                     data=f"{mese}-{rng.randint(1,28):02d}", kpi="gas_bweb"))
                elif g <= 94:
                    feed.append(dict(_i=i, tipo="attivazione", partecipante=ag,
                                     data=f"{mese}-{rng.randint(1,28):02d}", kpi="power_rid"))
                else:
                    feed.append(dict(_i=i, tipo="attivazione", partecipante=ag,
                                     data=f"{mese}-{rng.randint(1,28):02d}", kpi="gas_rid"))
    # un'agenzia cessa a fine aprile (perde i punti) e riattiva a maggio (li riprende)
    feed.append(dict(_i=9001, tipo="cessazione", partecipante="AG-007", data="2026-04-29"))
    feed.append(dict(_i=9002, tipo="riattivazione", partecipante="AG-007", data="2026-05-12"))
    # un'agenzia cessa a fine periodo (punti persi definitivamente)
    feed.append(dict(_i=9003, tipo="cessazione", partecipante="AG-011", data="2026-05-29"))
    return feed
    # NOTA (finding per il cliente): se un contratto è attivato DOPO la data di
    # cessazione, oggi il motore lo riaccumula. Il regolamento esclude gli agenti
    # cessati → domanda da sciogliere: le attivazioni post-cessazione contano? Va
    # gestita come escalation quando arrivano i dati reali con le date vere.


def esegui(db_path: Path, feed: list[dict]) -> tuple[Ledger, dict]:
    if db_path.exists():
        db_path.unlink()
        for ext in ("-wal", "-shm"):
            p = Path(str(db_path) + ext)
            if p.exists():
                p.unlink()
    contratto = yaml.safe_load(CONTRATTO.read_text())
    led = Ledger(db_path)
    riepilogo = motore_gara.esegui([contratto], feed, led, gara_id=GARA_ID,
                                   run_id="run_pilota_sintetico")
    return led, riepilogo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verifica-determinismo", action="store_true")
    args = ap.parse_args()

    if not CONTRATTO.exists():
        raise SystemExit(f"Contratto pilota non trovato: {CONTRATTO}\n"
                         "Compilare prima il regolamento (vedi mockup/01_contratto/compilatore.py).")

    feed = genera_feed_sintetico()

    if args.verifica_determinismo:
        l1, _ = esegui(GARA_DIR / "_det1.db", feed)
        l2, _ = esegui(GARA_DIR / "_det2.db", feed)
        s1, s2 = l1.saldi(GARA_ID), l2.saldi(GARA_ID)
        l1.close(); l2.close()
        (GARA_DIR / "_det1.db").unlink(); (GARA_DIR / "_det2.db").unlink()
        for ext in ("-wal", "-shm"):
            for n in ("_det1.db", "_det2.db"):
                p = GARA_DIR / (n + ext)
                if p.exists(): p.unlink()
        print("Determinismo:", "✓ identici" if s1 == s2 else "✗ DIVERSI", f"({len(s1)} partecipanti)")
        sys.exit(0 if s1 == s2 else 1)

    led, rip = esegui(DB, feed)
    saldi = led.saldi(GARA_ID)
    print("REGOLO — esecuzione pilota (feed SINTETICO, in attesa dati reali)\n")
    print(f"  Contratto: {yaml.safe_load(CONTRATTO.read_text())['meta']['gara']}")
    print(f"  Record processati: {rip['record_processati']} "
          f"(attivazioni {rip['attivazione']}, cessazioni {rip['cessazione']}, "
          f"riattivazioni {rip['riattivazione']})")
    print(f"  Eventi a ledger: {led.conteggio(GARA_ID)}  →  {DB.relative_to(ROOT)}")
    if rip["ignorati"]:
        print(f"  Contratti senza punti (es. <=25 kW, fuori fascia): {rip['ignorati']}")
    print(f"\n  Classifica saldi (top 12):")
    for pos, (ag, s) in enumerate(saldi.items(), 1):
        print(f"   {pos:2}. {ag}  {s:>8,} pt")
    # AG-007 (cessa+riattiva) deve avere saldo pieno; AG-011 (cessa) deve avere 0
    print(f"\n  Verifica storno/riaccredito:")
    print(f"   AG-007 (cessa 29/04 + riattiva 12/05): {saldi.get('AG-007', 0):,} pt (atteso: pieno)")
    print(f"   AG-011 (cessa 20/05, non riattiva):    {saldi.get('AG-011', 0):,} pt (atteso: 0)")
    led.close()


if __name__ == "__main__":
    main()
