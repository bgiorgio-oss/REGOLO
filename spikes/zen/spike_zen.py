#!/usr/bin/env python3
"""
SPIKE — GoRules ZEN Engine come motore L2 di REGOLO.

Domanda: il Contratto di Gara può essere transpilato in un decision model JDM
ed eseguito da ZEN Engine ottenendo ESATTAMENTE gli stessi numeri del nostro
motore deterministico?

Metodo:
  1. TRANSPILER: contratto YAML (v1 e v2) → JDM JSON. I parametri (punti, cap,
     moltiplicatori, soglie bonus) vengono LETTI dal contratto e cuciti nelle
     espressioni: il JDM è l'artefatto eseguibile, il contratto resta la fonte.
  2. RUNNER: per ogni PV × mese valuta il JDM giusto (effective dating: v1 fino
     a maggio, v2 da giugno — gestito dal NOSTRO layer, fuori da ZEN) e
     confronta meccanica per meccanica con gli eventi del ledger del motore.

Esito atteso: 0 divergenze su tutti i (pv, periodo, meccanica).
"""

import csv
import json
import time
from pathlib import Path

import yaml
import zen

QUI = Path(__file__).parent
ROOT = QUI.parent.parent
MOCKUP = ROOT / "mockup"
CONTRATTI = MOCKUP / "01_contratto"
DATI = MOCKUP / "02_dati"
LEDGER = MOCKUP / "output" / "ledger.jsonl"

MESI_CONCLUSI = ["2026-04", "2026-05"]
MESE_PARZIALE = "2026-06"
SOGLIA_ANOMALIA = 5  # stessa regola di quarantena del motore


# ---------------------------------------------------------------------------
# 1. TRANSPILER — contratto YAML → JDM (i parametri vengono dal contratto)
# ---------------------------------------------------------------------------

def meccanica(c: dict, mid: str) -> dict:
    return next(m for m in c["meccaniche"] if m["id"] == mid)


def transpila(contratto: dict) -> dict:
    """Genera il decision model JDM equivalente al contratto."""
    p_comm = meccanica(contratto, "punti_commodity")
    p_fibra = meccanica(contratto, "punti_fibra")
    p_fv = meccanica(contratto, "punti_fotovoltaico")
    p_wb = meccanica(contratto, "punti_wallbox")
    p_cl = meccanica(contratto, "punti_clima")
    b_ob = meccanica(contratto, "bonus_obiettivo_mensile")
    b_tr = meccanica(contratto, "bonus_tripletta")

    molt = (p_cl.get("moltiplicatori") or [{}])[0]
    mesi_molt = json.dumps([str(x) for x in molt.get("periodi", [])])
    fattore = molt.get("fattore", 1)

    espressioni = [
        ("punti_commodity",
         f"luce_gas > 0 ? min([luce_gas * {p_comm['punti']}, {p_comm['cap_mensile_punti']}]) : 0"),
        ("punti_fibra", f"fibra * {p_fibra['punti']}"),
        ("punti_fotovoltaico", f"fotovoltaico * {p_fv['punti']}"),
        ("punti_wallbox", f"wallbox * {p_wb['punti']}"),
        ("punti_clima",
         f"round(clima * {p_cl['punti']} * (periodo in {mesi_molt} ? {fattore} : 1))"),
        ("storni", f"-(storni_luce_gas * {p_comm['punti']} + storni_fibra * {p_fibra['punti']})"),
        ("bonus_obiettivo_mensile",
         f"mese_concluso and (luce_gas - storni_luce_gas) >= target ? {b_ob['punti']} : 0"),
        ("bonus_tripletta",
         "mese_concluso and fotovoltaico >= 1 and wallbox >= 1 and clima >= 1 "
         f"? {b_tr['punti']} : 0"),
    ]
    return {
        "nodes": [
            {"id": "in", "type": "inputNode", "name": "prestazioni_mese",
             "position": {"x": 0, "y": 0}},
            {"id": "calc", "type": "expressionNode", "name": "meccaniche",
             "position": {"x": 250, "y": 0},
             "content": {"expressions": [
                 {"id": f"e{i}", "key": k, "value": v} for i, (k, v) in enumerate(espressioni)]}},
            {"id": "out", "type": "outputNode", "name": "punti",
             "position": {"x": 500, "y": 0}},
        ],
        "edges": [
            {"id": "ed1", "sourceId": "in", "targetId": "calc"},
            {"id": "ed2", "sourceId": "calc", "targetId": "out"},
        ],
    }


# ---------------------------------------------------------------------------
# 2. RUNNER — esegue i JDM e confronta col ledger del motore
# ---------------------------------------------------------------------------

def main() -> None:
    contratti = {}
    for v, nome in ((1, "gara_spazio_alla_meta.v1.yaml"), (2, "gara_spazio_alla_meta.v2.yaml")):
        with open(CONTRATTI / nome) as f:
            contratti[v] = yaml.safe_load(f)

    # transpila e salva (artefatti ispezionabili)
    jdm = {}
    for v, c in contratti.items():
        jdm[v] = transpila(c)
        (QUI / f"zen_sam2026_v{v}.json").write_text(json.dumps(jdm[v], indent=1))
    engine = zen.ZenEngine()
    decisioni = {v: engine.create_decision(json.dumps(j)) for v, j in jdm.items()}

    # dati
    with open(DATI / "anagrafica.csv") as f:
        anagrafica = {r["codice_pv"]: r for r in csv.DictReader(f)}
    target_cluster = {c["id"]: c["target_mensile_commodity"]
                      for c in contratti[1]["cluster"]["definizioni"]}
    prestazioni = {}
    for periodo in MESI_CONCLUSI + [MESE_PARZIALE]:
        with open(DATI / f"prestazioni_{periodo}.csv") as f:
            prestazioni[periodo] = {r["codice_pv"]: {k: int(v) for k, v in r.items()
                                                     if k not in ("periodo", "codice_pv")}
                                    for r in csv.DictReader(f)}

    # quarantena (stessa regola del motore: esclusa dal confronto)
    quarantena = set()
    for codice, riga in prestazioni[MESE_PARZIALE].items():
        media = sum(prestazioni[p][codice]["luce_gas"] for p in MESI_CONCLUSI) / len(MESI_CONCLUSI)
        if riga["luce_gas"] > SOGLIA_ANOMALIA * max(media, 5):
            quarantena.add(codice)

    # atteso: eventi del motore aggregati per (pv, periodo, meccanica)
    atteso: dict[tuple, int] = {}
    for r in LEDGER.read_text().splitlines():
        e = json.loads(r)
        chiave = (e["pv"], e["periodo"], e["meccanica"])
        atteso[chiave] = atteso.get(chiave, 0) + e["punti"]

    # esecuzione ZEN
    ottenuto: dict[tuple, int] = {}
    t0 = time.time()
    valutazioni = 0
    for periodo in MESI_CONCLUSI + [MESE_PARZIALE]:
        v = 2 if periodo >= str(contratti[2]["meta"]["valido_dal"])[:7] else 1  # effective dating (nostro layer)
        for codice, riga in prestazioni[periodo].items():
            if periodo == MESE_PARZIALE and codice in quarantena:
                continue
            input_zen = dict(riga, periodo=periodo,
                             mese_concluso=periodo in MESI_CONCLUSI,
                             target=target_cluster[anagrafica[codice]["cluster"]])
            risultato = decisioni[v].evaluate(input_zen)["result"]
            valutazioni += 1
            for mecc, punti in risultato.items():
                if round(punti) != 0:
                    ottenuto[(codice, periodo, mecc)] = round(punti)
    durata_ms = (time.time() - t0) * 1000

    # confronto esatto
    chiavi = set(atteso) | set(ottenuto)
    divergenze = [(k, atteso.get(k), ottenuto.get(k)) for k in sorted(chiavi)
                  if atteso.get(k) != ottenuto.get(k)]

    print("SPIKE ZEN ENGINE — verdetto")
    print(f"  JDM generati dal contratto: v1, v2 (salvati in {QUI.relative_to(ROOT)}/)")
    print(f"  Valutazioni ZEN: {valutazioni} (PV × mese) in {durata_ms:.0f} ms "
          f"({durata_ms / valutazioni:.2f} ms/valutazione)")
    print(f"  Celle confrontate (pv, periodo, meccanica): {len(chiavi)}")
    print(f"  Eventi del motore coperti: {sum(1 for _ in LEDGER.read_text().splitlines())}")
    if divergenze:
        print(f"  ✗ DIVERGENZE: {len(divergenze)}")
        for k, a, o in divergenze[:15]:
            print(f"    {k}: motore={a} zen={o}")
        raise SystemExit(1)
    print("  ✓ ZERO DIVERGENZE: ZEN riproduce il motore al 100%")


if __name__ == "__main__":
    main()
