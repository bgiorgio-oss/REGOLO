#!/usr/bin/env python3
"""
REGOLO — GOLDEN TEST DI GARA a doppio motore.

Esegue ogni caso di casi_sam2026.yaml su:
  1. il motore Python del mockup (calcola_mese)
  2. ZEN Engine sul JDM transpilato dal contratto (transpiler dello spike)
e verifica che ENTRAMBI coincidano con l'atteso (e quindi tra loro).

Due implementazioni indipendenti che devono dare lo stesso numero: è la
riconciliazione interna che accompagnerà ogni modifica di contratto o motore.

Uso: venv/bin/python tests/golden/run_golden.py
Exit code 0 = tutti verdi.
"""

import importlib.util
import json
import sys
from pathlib import Path

import yaml
import zen

QUI = Path(__file__).parent
ROOT = QUI.parent.parent
CONTRATTI = ROOT / "mockup" / "01_contratto"

CAMPI_INPUT = ["luce_gas", "fibra", "fotovoltaico", "wallbox", "clima",
               "storni_luce_gas", "storni_fibra"]


def importa(nome: str, percorso: Path):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


motore = importa("motore", ROOT / "mockup" / "03_motore" / "motore.py")
spike_zen = importa("spike_zen", ROOT / "spikes" / "zen" / "spike_zen.py")


def main() -> None:
    casi = yaml.safe_load((QUI / "casi_sam2026.yaml").read_text())
    contratti = {}
    for v in (1, 2):
        with open(CONTRATTI / f"gara_spazio_alla_meta.v{v}.yaml") as f:
            contratti[v] = yaml.safe_load(f)
    engine = zen.ZenEngine()
    decisioni = {v: engine.create_decision(json.dumps(spike_zen.transpila(c)))
                 for v, c in contratti.items()}

    falliti = 0
    print(f"GOLDEN TEST SAM2026 — {len(casi)} casi × 2 motori (Python + ZEN)\n")
    for caso in casi:
        v = caso["contratto_v"]
        contratto = contratti[v]

        # coerenza con l'effective dating dichiarato nel contratto
        v_effettiva = 2 if caso["periodo"] >= str(contratti[2]["meta"]["valido_dal"])[:7] else 1
        assert v == v_effettiva, f"{caso['nome']}: contratto_v={v} ma il periodo implica v{v_effettiva}"

        riga = {k: caso["input"].get(k, 0) for k in CAMPI_INPUT}
        cluster_def = {"id": "TEST", "target_mensile_commodity": caso["target"]}

        # --- motore Python ---
        eventi = motore.calcola_mese(contratto, cluster_def, riga, caso["periodo"],
                                     caso["mese_concluso"])
        py = {}
        for e in eventi:
            py[e["meccanica"]] = py.get(e["meccanica"], 0) + e["punti"]
        py = {k: v_ for k, v_ in py.items() if v_ != 0}

        # --- ZEN / JDM ---
        out = decisioni[v].evaluate(dict(riga, periodo=caso["periodo"],
                                         mese_concluso=caso["mese_concluso"],
                                         target=caso["target"]))["result"]
        zen_ris = {k: round(v_) for k, v_ in out.items() if round(v_) != 0}

        atteso = caso["atteso"]
        ok_py, ok_zen = py == atteso, zen_ris == atteso
        if ok_py and ok_zen:
            print(f"  ✓ {caso['nome']}")
        else:
            falliti += 1
            print(f"  ✗ {caso['nome']} — {caso['descrizione']}")
            if not ok_py:
                print(f"      motore: {py}  ≠  atteso: {atteso}")
            if not ok_zen:
                print(f"      zen:    {zen_ris}  ≠  atteso: {atteso}")

    print(f"\n{'✓ TUTTI VERDI' if not falliti else f'✗ {falliti} FALLITI'} "
          f"— {len(casi) - falliti}/{len(casi)} casi, entrambi i motori")
    sys.exit(1 if falliti else 0)


if __name__ == "__main__":
    main()
