#!/usr/bin/env python3
"""
REGOLO mockup — generatore dei dati fittizi della gara SAM2026.

Genera, con seed fisso (riproducibile):
  - anagrafica.csv                25 punti vendita Spazio Enel Partner (FITTIZI)
  - prestazioni_2026-04.csv       prestazioni mensili di aprile (mese concluso)
  - prestazioni_2026-05.csv       prestazioni mensili di maggio (mese concluso)
  - prestazioni_2026-06.csv       prestazioni di giugno PARZIALI (dati al 07/06)
  - piattaforma_export.csv        punteggi apr+mag calcolati dalla PIATTAFORMA legacy
                                  (simulata: stessa logica v1 ma con 2 ERRORI INTENZIONALI,
                                  che la riconciliazione del motore deve trovare)

NOTA — duplicazione intenzionale: il calcolo in fondo a questo file simula il motore
INDIPENDENTE della piattaforma legacy. È proprio ciò che la riconciliazione confronta.
"""

import csv
import random
from pathlib import Path

QUI = Path(__file__).parent
RNG = random.Random(2026)  # seed fisso: dati identici a ogni rigenerazione

# ---------------------------------------------------------------------------
# Anagrafica — 25 PV fittizi su 3 cluster
# ---------------------------------------------------------------------------

PV = [
    # (codice, insegna, citta, prov, regione, cluster)
    ("SE-MI-001", "Spazio Enel Milano Duomo",        "Milano",        "MI", "Lombardia",      "GOLD"),
    ("SE-RM-001", "Spazio Enel Roma Prati",          "Roma",          "RM", "Lazio",          "GOLD"),
    ("SE-TO-001", "Spazio Enel Torino Centro",       "Torino",        "TO", "Piemonte",       "GOLD"),
    ("SE-NA-001", "Spazio Enel Napoli Vomero",       "Napoli",        "NA", "Campania",       "GOLD"),
    ("SE-BO-001", "Spazio Enel Bologna Marconi",     "Bologna",       "BO", "Emilia-Romagna", "GOLD"),
    ("SE-FI-001", "Spazio Enel Firenze Novoli",      "Firenze",       "FI", "Toscana",        "GOLD"),
    ("SE-PA-001", "Spazio Enel Palermo Libertà",     "Palermo",       "PA", "Sicilia",        "GOLD"),
    ("SE-MI-002", "Spazio Enel Milano Bicocca",      "Milano",        "MI", "Lombardia",      "SILVER"),
    ("SE-RM-002", "Spazio Enel Roma Eur",            "Roma",          "RM", "Lazio",          "SILVER"),
    ("SE-RM-003", "Spazio Enel Roma Tuscolana",      "Roma",          "RM", "Lazio",          "SILVER"),
    ("SE-VR-001", "Spazio Enel Verona Borgo Roma",   "Verona",        "VR", "Veneto",         "SILVER"),
    ("SE-BA-001", "Spazio Enel Bari Poggiofranco",   "Bari",          "BA", "Puglia",         "SILVER"),
    ("SE-CT-001", "Spazio Enel Catania Etnea",       "Catania",       "CT", "Sicilia",        "SILVER"),
    ("SE-GE-001", "Spazio Enel Genova Sampierdarena","Genova",        "GE", "Liguria",        "SILVER"),
    ("SE-PD-001", "Spazio Enel Padova Stanga",       "Padova",        "PD", "Veneto",         "SILVER"),
    ("SE-BS-001", "Spazio Enel Brescia Due",         "Brescia",       "BS", "Lombardia",      "SILVER"),
    ("SE-AN-001", "Spazio Enel Ancona Baraccola",    "Ancona",        "AN", "Marche",         "BRONZE"),
    ("SE-PG-001", "Spazio Enel Perugia Fontivegge",  "Perugia",       "PG", "Umbria",         "BRONZE"),
    ("SE-CA-001", "Spazio Enel Cagliari Marconi",    "Cagliari",      "CA", "Sardegna",       "BRONZE"),
    ("SE-TS-001", "Spazio Enel Trieste Borgo",       "Trieste",       "TS", "Friuli-V.G.",    "BRONZE"),
    ("SE-RE-001", "Spazio Enel Reggio Emilia Sud",   "Reggio Emilia", "RE", "Emilia-Romagna", "BRONZE"),
    ("SE-LE-001", "Spazio Enel Lecce Mazzini",       "Lecce",         "LE", "Puglia",         "BRONZE"),
    ("SE-PE-001", "Spazio Enel Pescara Centro",      "Pescara",       "PE", "Abruzzo",        "BRONZE"),
    ("SE-VI-001", "Spazio Enel Vicenza Ovest",       "Vicenza",       "VI", "Veneto",         "BRONZE"),
    ("SE-SA-001", "Spazio Enel Salerno Irno",        "Salerno",       "SA", "Campania",       "BRONZE"),
]

# range media 2025 coerenti con i criteri di cluster del contratto (art. 4.1)
MEDIA_2025 = {"GOLD": (60, 90), "SILVER": (30, 59), "BRONZE": (12, 29)}

# range di generazione prestazioni mensili per cluster
# (lg=luce_gas, fb=fibra, fv=fotovoltaico, wb=wallbox, cl=clima, slg/sfb=storni)
RANGE = {
    "GOLD":   dict(lg=(65, 95), fb=(14, 28), fv=(1, 4), wb=(0, 3), cl=(2, 6), slg=(0, 4), sfb=(0, 1)),
    "SILVER": dict(lg=(40, 65), fb=(8, 18),  fv=(0, 2), wb=(0, 2), cl=(1, 4), slg=(0, 3), sfb=(0, 1)),
    "BRONZE": dict(lg=(18, 38), fb=(3, 10),  fv=(0, 1), wb=(0, 1), cl=(0, 3), slg=(0, 2), sfb=(0, 1)),
}
# a giugno fa caldo: range clima più alto (prima del fattore mese parziale)
RANGE_CL_GIU = {"GOLD": (4, 9), "SILVER": (3, 7), "BRONZE": (2, 5)}

FATTORE_GIUGNO = 0.25  # dati parziali: prima settimana (al 07/06)


def genera_mese(cluster: str, periodo: str) -> dict:
    """Genera una riga prestazioni casuale (ma con seed) per un PV di un cluster."""
    r = RANGE[cluster]
    cl_range = RANGE_CL_GIU[cluster] if periodo == "2026-06" else r["cl"]
    riga = dict(
        luce_gas=RNG.randint(*r["lg"]),
        fibra=RNG.randint(*r["fb"]),
        fotovoltaico=RNG.randint(*r["fv"]),
        wallbox=RNG.randint(*r["wb"]),
        clima=RNG.randint(*cl_range),
        storni_luce_gas=RNG.randint(*r["slg"]),
        storni_fibra=RNG.randint(*r["sfb"]),
    )
    if periodo == "2026-06":  # mese parziale: scala tutto
        for k in riga:
            riga[k] = round(riga[k] * FATTORE_GIUGNO)
    return riga


def main() -> None:
    # ----- anagrafica ------------------------------------------------------
    with open(QUI / "anagrafica.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["codice_pv", "insegna", "citta", "provincia", "regione",
                    "cluster", "media_2025", "email_referente", "data_adesione", "stato"])
        for codice, insegna, citta, prov, reg, cluster in PV:
            w.writerow([codice, insegna, citta, prov, reg, cluster,
                        RNG.randint(*MEDIA_2025[cluster]),
                        f"{codice.lower()}@spazioenel-mock.example", "2026-03-15", "attivo"])

    # ----- prestazioni mensili --------------------------------------------
    prestazioni: dict[str, dict[str, dict]] = {}  # periodo -> codice_pv -> riga
    for periodo in ("2026-04", "2026-05", "2026-06"):
        prestazioni[periodo] = {}
        for codice, _, _, _, _, cluster in PV:
            prestazioni[periodo][codice] = genera_mese(cluster, periodo)

    # --- righe pilotate (servono alla storia della demo) ---
    # SE-MI-001: il PV "protagonista" del frontend — leader del cluster GOLD, tripletta apr+mag
    prestazioni["2026-04"]["SE-MI-001"] = dict(luce_gas=92, fibra=26, fotovoltaico=3, wallbox=2,
                                               clima=5, storni_luce_gas=1, storni_fibra=0)
    prestazioni["2026-05"]["SE-MI-001"] = dict(luce_gas=95, fibra=28, fotovoltaico=4, wallbox=2,
                                               clima=6, storni_luce_gas=2, storni_fibra=0)
    prestazioni["2026-06"]["SE-MI-001"] = dict(luce_gas=24, fibra=7, fotovoltaico=1, wallbox=1,
                                               clima=2, storni_luce_gas=0, storni_fibra=0)
    # SE-NA-001: in aprile supera largamente il cap (servirà alla divergenza "cap sbagliato")
    prestazioni["2026-04"]["SE-NA-001"]["luce_gas"] = 78
    # SE-MI-002: 3 storni a maggio (servirà alla divergenza "storno non applicato")
    prestazioni["2026-05"]["SE-MI-002"]["storni_luce_gas"] = 3
    # SE-RM-003: ANOMALIA a giugno — valore fuori scala che il motore deve mettere in quarantena
    prestazioni["2026-06"]["SE-RM-003"]["luce_gas"] = 380

    for periodo, righe in prestazioni.items():
        with open(QUI / f"prestazioni_{periodo}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["periodo", "codice_pv", "luce_gas", "fibra", "fotovoltaico",
                        "wallbox", "clima", "storni_luce_gas", "storni_fibra"])
            for codice, r in righe.items():
                w.writerow([periodo, codice, r["luce_gas"], r["fibra"], r["fotovoltaico"],
                            r["wallbox"], r["clima"], r["storni_luce_gas"], r["storni_fibra"]])

    # ----- export della PIATTAFORMA legacy (apr+mag) -----------------------
    # Simula il calcolo INDIPENDENTE della piattaforma con le regole v1.
    # Due errori intenzionali (sono "bug della piattaforma" che la riconciliazione trova):
    #   1. SE-MI-002: a maggio NON applica 3 storni commodity        → +30 punti
    #   2. SE-NA-001: ad aprile applica il cap a 650 invece di 600   → +50 punti
    TARGET = {"GOLD": 80, "SILVER": 50, "BRONZE": 30}

    def punti_mese_v1(cluster: str, r: dict, cap: int = 600) -> int:
        lordi_commodity = min(r["luce_gas"] * 10, cap)
        storni = r["storni_luce_gas"] * 10 + r["storni_fibra"] * 20
        base = (lordi_commodity + r["fibra"] * 20 + r["fotovoltaico"] * 150
                + r["wallbox"] * 60 + r["clima"] * 40 - storni)
        bonus = 0
        if (r["luce_gas"] - r["storni_luce_gas"]) >= TARGET[cluster]:
            bonus += 200
        if r["fotovoltaico"] >= 1 and r["wallbox"] >= 1 and r["clima"] >= 1:
            bonus += 100
        return base + bonus

    with open(QUI / "piattaforma_export.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["codice_pv", "punti_apr_mag"])
        for codice, _, _, _, _, cluster in PV:
            apr, mag = prestazioni["2026-04"][codice], prestazioni["2026-05"][codice]
            if codice == "SE-NA-001":
                tot = punti_mese_v1(cluster, apr, cap=650) + punti_mese_v1(cluster, mag)  # errore 2
            elif codice == "SE-MI-002":
                mag_no_storni = dict(mag, storni_luce_gas=0)                              # errore 1
                tot = punti_mese_v1(cluster, apr) + punti_mese_v1(cluster, mag_no_storni)
            else:
                tot = punti_mese_v1(cluster, apr) + punti_mese_v1(cluster, mag)
            w.writerow([codice, tot])

    print("✓ Dati mock generati in", QUI)
    print("  - anagrafica.csv (25 PV)")
    print("  - prestazioni_2026-04/05/06.csv (giugno parziale, con anomalia SE-RM-003)")
    print("  - piattaforma_export.csv (con 2 divergenze intenzionali: SE-MI-002, SE-NA-001)")


if __name__ == "__main__":
    main()
