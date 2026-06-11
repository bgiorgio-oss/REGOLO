#!/usr/bin/env python3
"""
REGOLO — MOTORE DETERMINISTICO (L2) — mockup, ma il calcolo è vero.

Legge i Contratti di Gara (YAML, v1+v2) e i dati di prestazione, e produce:
  - output/ledger.jsonl   eventi append-only (L3): accrediti, storni, bonus
  - output/state.json     stato derivato per l'API (L4): saldi, classifiche,
                          riconciliazione vs piattaforma legacy, what-if, alert

Proprietà dimostrate qui dentro (le stesse del sistema reale):
  * ZERO AI a runtime: solo i parametri del contratto guidano il calcolo
  * effective dating: aprile/maggio → contratto v1, da giugno → v2
  * mese parziale: solo accrediti unitari e storni; i bonus si liquidano a mese concluso
  * quarantena: input fuori scala esclusi dal calcolo e segnalati
  * HITL: i mesi non ancora validati restano "in_approvazione"
  * riconciliazione: confronto col calcolo indipendente della piattaforma legacy,
    con diagnosi automatica delle divergenze
  * what-if: replay integrale con la v2 retroattiva → delta punti e budget
"""

import copy
import csv
import json
from pathlib import Path

import yaml

QUI = Path(__file__).parent
MOCKUP = QUI.parent
DATI = MOCKUP / "02_dati"
CONTRATTI = MOCKUP / "01_contratto"
OUTPUT = MOCKUP / "output"

# Data di riferimento FISSA del mockup (determinismo: niente datetime.now())
DATA_RIFERIMENTO = "2026-06-10"
MESI_CONCLUSI = ["2026-04", "2026-05"]
MESE_PARZIALE = "2026-06"           # dati alla prima settimana (07/06)
GIORNI_RIMANENTI = 112              # dal 10/06 al 30/09
TS_ELABORAZIONE = {"2026-04": "2026-05-04T09:00:00", "2026-05": "2026-06-04T09:00:00",
                   "2026-06": "2026-06-08T09:00:00"}
SOGLIA_ANOMALIA = 5                 # input > 5x media storica → quarantena

# ---------------------------------------------------------------------------
# Caricamento contratti e dati
# ---------------------------------------------------------------------------

def carica_contratti() -> list[dict]:
    contratti = []
    for nome in ("gara_spazio_alla_meta.v1.yaml", "gara_spazio_alla_meta.v2.yaml"):
        with open(CONTRATTI / nome) as f:
            contratti.append(yaml.safe_load(f))
    return contratti


def contratto_per(periodo: str, contratti: list[dict]) -> dict:
    """Effective dating: il contratto con la versione più alta valido nel periodo."""
    validi = [c for c in contratti if str(c["meta"]["valido_dal"])[:7] <= periodo]
    return max(validi, key=lambda c: c["meta"]["contratto_versione"])


def carica_anagrafica() -> dict[str, dict]:
    with open(DATI / "anagrafica.csv") as f:
        return {r["codice_pv"]: r for r in csv.DictReader(f)}


def carica_prestazioni() -> dict[str, dict[str, dict]]:
    """periodo -> codice_pv -> riga (valori interi)."""
    out: dict[str, dict[str, dict]] = {}
    for periodo in MESI_CONCLUSI + [MESE_PARZIALE]:
        with open(DATI / f"prestazioni_{periodo}.csv") as f:
            out[periodo] = {}
            for r in csv.DictReader(f):
                out[periodo][r["codice_pv"]] = {k: int(v) for k, v in r.items()
                                                if k not in ("periodo", "codice_pv")}
    return out


# ---------------------------------------------------------------------------
# Calcolo di un mese per un PV — guidato SOLO dai parametri del contratto
# ---------------------------------------------------------------------------

def meccanica(contratto: dict, mid: str) -> dict:
    return next(m for m in contratto["meccaniche"] if m["id"] == mid)


def punti_unitari_clima(contratto: dict, periodo: str) -> float:
    m = meccanica(contratto, "punti_clima")
    punti = m["punti"]
    for molt in m.get("moltiplicatori", []):
        if periodo in molt["periodi"]:
            punti *= molt["fattore"]
    return punti


def calcola_mese(contratto: dict, cluster_def: dict, riga: dict, periodo: str,
                 mese_concluso: bool) -> list[dict]:
    """Ritorna gli eventi (senza id/ts/stato) del mese per un PV."""
    eventi = []
    v = contratto["meta"]["contratto_versione"]

    def ev(tipo, mecc, punti, descr):
        eventi.append(dict(tipo=tipo, meccanica=mecc, punti=round(punti),
                           descrizione=descr, contratto_v=v, periodo=periodo))

    # --- accrediti unitari ---
    m_comm = meccanica(contratto, "punti_commodity")
    cap = m_comm["cap_mensile_punti"]
    lordi = riga["luce_gas"] * m_comm["punti"]
    accreditati = min(lordi, cap)
    nota_cap = f" (cap {cap} applicato, lordi {lordi})" if lordi > cap else ""
    if riga["luce_gas"]:
        ev("accredito", "punti_commodity", accreditati,
           f"{riga['luce_gas']} attivazioni commodity × {m_comm['punti']} pt{nota_cap}")

    if riga["fibra"]:
        p = meccanica(contratto, "punti_fibra")["punti"]
        ev("accredito", "punti_fibra", riga["fibra"] * p, f"{riga['fibra']} attivazioni fibra × {p} pt")
    if riga["fotovoltaico"]:
        p = meccanica(contratto, "punti_fotovoltaico")["punti"]
        ev("accredito", "punti_fotovoltaico", riga["fotovoltaico"] * p,
           f"{riga['fotovoltaico']} fotovoltaico × {p} pt")
    if riga["wallbox"]:
        p = meccanica(contratto, "punti_wallbox")["punti"]
        ev("accredito", "punti_wallbox", riga["wallbox"] * p, f"{riga['wallbox']} wallbox × {p} pt")
    if riga["clima"]:
        pu = punti_unitari_clima(contratto, periodo)
        extra = " (acceleratore estivo ×1,5)" if pu != meccanica(contratto, "punti_clima")["punti"] else ""
        ev("accredito", "punti_clima", riga["clima"] * pu, f"{riga['clima']} clima × {pu:g} pt{extra}")

    # --- storni (fuori cap, art. 5.6/5.7) ---
    storno_pt = (riga["storni_luce_gas"] * m_comm["punti"]
                 + riga["storni_fibra"] * meccanica(contratto, "punti_fibra")["punti"])
    if storno_pt:
        ev("storno", "storni", -storno_pt,
           f"{riga['storni_luce_gas']} storni commodity + {riga['storni_fibra']} storni fibra "
           f"(annullamenti entro 60 gg dall'attivazione)")

    # --- bonus: solo a mese concluso (art. 6.4) ---
    if mese_concluso:
        m_ob = meccanica(contratto, "bonus_obiettivo_mensile")
        nette = riga["luce_gas"] - riga["storni_luce_gas"]
        target = cluster_def["target_mensile_commodity"]
        if nette >= target:
            ev("bonus", "bonus_obiettivo_mensile", m_ob["punti"],
               f"obiettivo mensile raggiunto ({nette} attivazioni nette ≥ target {target})")
        m_tr = meccanica(contratto, "bonus_tripletta")
        if riga["fotovoltaico"] >= 1 and riga["wallbox"] >= 1 and riga["clima"] >= 1:
            ev("bonus", "bonus_tripletta", m_tr["punti"],
               "tripletta: fotovoltaico + wallbox + clima nello stesso mese")
    return eventi


# ---------------------------------------------------------------------------
# Run completo (per la modalità effective e per i what-if)
# ---------------------------------------------------------------------------

def esegui_run(contratti: list[dict], anagrafica: dict, prestazioni: dict,
               quarantena: set[str], strategia: str = "effective") -> dict[str, dict[str, list[dict]]]:
    """codice_pv -> periodo -> eventi. strategia: 'effective' | 'v2_retroattivo'."""
    risultati: dict[str, dict[str, list[dict]]] = {}
    for periodo in MESI_CONCLUSI + [MESE_PARZIALE]:
        if strategia == "v2_retroattivo":
            contratto = max(contratti, key=lambda c: c["meta"]["contratto_versione"])
        else:
            contratto = contratto_per(periodo, contratti)
        for codice, riga in prestazioni[periodo].items():
            if periodo == MESE_PARZIALE and codice in quarantena:
                continue  # input anomalo: escluso dal calcolo
            anag = anagrafica[codice]
            cluster_def = next(c for c in contratto["cluster"]["definizioni"]
                               if c["id"] == anag["cluster"])
            eventi = calcola_mese(contratto, cluster_def, riga, periodo,
                                  mese_concluso=periodo in MESI_CONCLUSI)
            risultati.setdefault(codice, {})[periodo] = eventi
    return risultati


def totale(eventi_pv: dict[str, list[dict]], periodi: list[str]) -> int:
    return sum(e["punti"] for p in periodi for e in eventi_pv.get(p, []))


# ---------------------------------------------------------------------------
# Quarantena anomalie sugli input del mese parziale
# ---------------------------------------------------------------------------

def rileva_anomalie(prestazioni: dict) -> tuple[set[str], list[dict]]:
    quarantena, alert = set(), []
    for codice, riga in prestazioni[MESE_PARZIALE].items():
        storico = [prestazioni[p][codice]["luce_gas"] for p in MESI_CONCLUSI]
        media = sum(storico) / len(storico)
        soglia = SOGLIA_ANOMALIA * max(media, 5)
        if riga["luce_gas"] > soglia:
            quarantena.add(codice)
            alert.append(dict(
                tipo="anomalia_dati", pv=codice, periodo=MESE_PARZIALE, stato="quarantena",
                dettaglio=(f"luce_gas={riga['luce_gas']} nel flusso di giugno vs media storica "
                           f"{media:.0f}/mese (soglia {soglia:.0f}). Riga esclusa dal calcolo "
                           f"in attesa di verifica col Promotore."),
            ))
    return quarantena, alert


# ---------------------------------------------------------------------------
# Riconciliazione con la piattaforma legacy + diagnosi automatica
# ---------------------------------------------------------------------------

def riconcilia(contratti, anagrafica, prestazioni, eventi_eff) -> dict:
    with open(DATI / "piattaforma_export.csv") as f:
        piattaforma = {r["codice_pv"]: int(r["punti_apr_mag"]) for r in csv.DictReader(f)}

    def punti_variante(codice: str, modifica) -> int:
        """Ricalcola apr+mag per un PV applicando una modifica agli input/contratto (ipotesi diagnostica)."""
        tot = 0
        for periodo in MESI_CONCLUSI:
            contratto = contratto_per(periodo, contratti)
            riga = dict(prestazioni[periodo][codice])
            contratto_mod, riga = modifica(periodo, copy.deepcopy(contratto), riga)
            anag = anagrafica[codice]
            cdef = next(c for c in contratto_mod["cluster"]["definizioni"] if c["id"] == anag["cluster"])
            tot += sum(e["punti"] for e in calcola_mese(contratto_mod, cdef, riga, periodo, True))
        return tot

    righe, divergenze = [], 0
    for codice in sorted(piattaforma):
        nostro = totale(eventi_eff[codice], MESI_CONCLUSI)
        loro = piattaforma[codice]
        delta = loro - nostro
        riga_out = dict(pv=codice, insegna=anagrafica[codice]["insegna"],
                        punti_regolo=nostro, punti_piattaforma=loro, delta=delta,
                        esito="OK" if delta == 0 else "KO")
        if delta != 0:
            divergenze += 1
            # Diagnosi automatica: ricalcola con ipotesi di errore note e tiene
            # SOLO quelle che spiegano ESATTAMENTE il valore della piattaforma.
            def cap_650_aprile(periodo, c, r):
                if periodo == "2026-04":
                    next(m for m in c["meccaniche"] if m["id"] == "punti_commodity")["cap_mensile_punti"] = 650
                return c, r

            def storni_commodity_ignorati_maggio(periodo, c, r):
                if periodo == "2026-05":
                    r["storni_luce_gas"] = 0
                return c, r

            def msg_storni() -> str:
                n = prestazioni["2026-05"][codice]["storni_luce_gas"]
                msg = (f"La piattaforma non ha applicato gli storni commodity di maggio "
                       f"({n} contratti annullati → {n * 10} pt non stornati)")
                if delta == n * 10 + 200:
                    msg += " e, di conseguenza, ha riconosciuto un bonus obiettivo non dovuto (+200 pt)"
                return msg + "."

            ipotesi = [
                (cap_650_aprile, "La piattaforma ha applicato ad aprile un cap commodity errato "
                                 "(650 invece di 600 → +50 pt)."),
                (storni_commodity_ignorati_maggio, None),  # messaggio costruito dinamicamente
            ]
            diagnosi = [msg if msg else msg_storni()
                        for fn, msg in ipotesi if punti_variante(codice, fn) == loro]
            riga_out["diagnosi"] = " / ".join(diagnosi) if diagnosi else \
                "Divergenza non spiegata automaticamente: richiede analisi manuale."
        righe.append(riga_out)

    return dict(periodi=MESI_CONCLUSI, pv_totali=len(righe), allineati=len(righe) - divergenze,
                divergenze=divergenze, righe=righe)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    contratti = carica_contratti()
    anagrafica = carica_anagrafica()
    prestazioni = carica_prestazioni()

    quarantena, alerts = rileva_anomalie(prestazioni)

    # run "effective": v1 per aprile/maggio, v2 da giugno
    eff = esegui_run(contratti, anagrafica, prestazioni, quarantena, "effective")
    # run what-if: v2 retroattiva su tutta la gara (replay)
    retro = esegui_run(contratti, anagrafica, prestazioni, quarantena, "v2_retroattivo")

    # ----- ledger append-only ----------------------------------------------
    run_id = f"run_{DATA_RIFERIMENTO.replace('-', '')}_effective"
    ledger, contatore = [], 0
    for codice in sorted(eff):
        for periodo in MESI_CONCLUSI + [MESE_PARZIALE]:
            for e in eff[codice].get(periodo, []):
                contatore += 1
                ledger.append(dict(
                    id=f"EV{contatore:05d}", ts=TS_ELABORAZIONE[periodo], gara="SAM2026",
                    pv=codice, run_id=run_id,
                    stato="contabilizzato" if periodo in MESI_CONCLUSI else "in_approvazione",
                    **e))
    with open(OUTPUT / "ledger.jsonl", "w") as f:
        for evento in ledger:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")

    # ----- stato per PV ------------------------------------------------------
    tasso = contratti[-1]["valorizzazione"]["tasso_eur_per_punto"]
    stato_pv = {}
    for codice, anag in anagrafica.items():
        contab = totale(eff[codice], MESI_CONCLUSI)
        in_appr = totale(eff[codice], [MESE_PARZIALE])
        breakdown: dict[str, int] = {}
        for periodo, eventi in eff[codice].items():
            for e in eventi:
                breakdown[e["meccanica"]] = breakdown.get(e["meccanica"], 0) + e["punti"]
        mesi = []
        for periodo in MESI_CONCLUSI + [MESE_PARZIALE]:
            riga = prestazioni[periodo].get(codice)
            in_q = periodo == MESE_PARZIALE and codice in quarantena
            target = int(next(c for c in contratti[0]["cluster"]["definizioni"]
                              if c["id"] == anag["cluster"])["target_mensile_commodity"])
            mesi.append(dict(
                periodo=periodo, parziale=periodo == MESE_PARZIALE, quarantena=in_q,
                punti=0 if in_q else totale(eff[codice], [periodo]),
                attivazioni_nette=0 if in_q else riga["luce_gas"] - riga["storni_luce_gas"],
                target=target))
        movimenti = [e for e in ledger if e["pv"] == codice][::-1]
        stato_pv[codice] = dict(
            codice=codice, insegna=anag["insegna"], citta=anag["citta"],
            cluster=anag["cluster"],
            provincia=anag["provincia"], regione=anag["regione"],
            email=anag["email_referente"], media_2025=int(anag["media_2025"]),
            data_adesione=anag["data_adesione"], stato_pv=anag["stato"],
            saldo_contabilizzato=contab, saldo_in_approvazione=in_appr,
            valore_eur=round(contab * tasso, 2), breakdown=breakdown, mesi=mesi,
            movimenti=movimenti)

    # ----- classifiche per cluster (mesi conclusi) ---------------------------
    classifiche = {}
    for cluster in ("GOLD", "SILVER", "BRONZE"):
        target = next(c for c in contratti[0]["cluster"]["definizioni"]
                      if c["id"] == cluster)["target_mensile_commodity"]
        membri = [dict(pv=c, insegna=a["insegna"], citta=a["citta"],
                       punti=totale(eff[c], MESI_CONCLUSI),
                       indice=round(totale(eff[c], MESI_CONCLUSI) / (target * len(MESI_CONCLUSI)), 2))
                  for c, a in anagrafica.items() if a["cluster"] == cluster]
        membri.sort(key=lambda m: -m["punti"])
        for pos, m in enumerate(membri, 1):
            m["posizione"] = pos
            stato_pv[m["pv"]]["posizione_classifica"] = pos
            stato_pv[m["pv"]]["dimensione_cluster"] = len(membri)
        classifiche[cluster] = membri

    # ----- riconciliazione e what-if -----------------------------------------
    riconciliazione = riconcilia(contratti, anagrafica, prestazioni, eff)

    whatif_righe = []
    for codice in sorted(eff):
        v_eff = totale(eff[codice], MESI_CONCLUSI)
        v_retro = totale(retro[codice], MESI_CONCLUSI)
        whatif_righe.append(dict(pv=codice, insegna=anagrafica[codice]["insegna"],
                                 cluster=anagrafica[codice]["cluster"],
                                 punti_v1=v_eff, punti_v2_retro=v_retro, delta=v_retro - v_eff))
    whatif_righe.sort(key=lambda r: -r["delta"])
    delta_tot = sum(r["delta"] for r in whatif_righe)
    whatif = dict(
        descrizione=("Replay: cosa sarebbe successo ad aprile e maggio se la revisione v2 "
                     "(cap 900, fotovoltaico 200 pt) fosse stata attiva dall'inizio della gara"),
        delta_punti_totale=delta_tot, delta_budget_eur=round(delta_tot * tasso, 2),
        pv_impattati=sum(1 for r in whatif_righe if r["delta"]), righe=whatif_righe)

    # ----- approvazioni HITL --------------------------------------------------
    appr_giugno_punti = sum(totale(eff[c], [MESE_PARZIALE]) for c in eff)
    approvazioni = [
        dict(batch="Credito Aprile 2026", stato="approvato", approvato_da="b.giorgio",
             approvato_il="2026-05-05", punti=sum(totale(eff[c], ["2026-04"]) for c in eff)),
        dict(batch="Credito Maggio 2026", stato="approvato", approvato_da="b.giorgio",
             approvato_il="2026-06-04", punti=sum(totale(eff[c], ["2026-05"]) for c in eff)),
        dict(batch="Credito Giugno 2026 (parziale, dati al 07/06)", stato="in_attesa",
             punti=appr_giugno_punti, valore_eur=round(appr_giugno_punti * tasso, 2),
             pv_coinvolti=sum(1 for c in eff if eff[c].get(MESE_PARZIALE)),
             nota=f"{len(quarantena)} PV in quarantena escluso/i dal batch"),
    ]

    # ----- catalogo e comunicazioni (statici nel mockup) ----------------------
    catalogo = [
        dict(id="gift25", emoji="🎁", nome="Gift card multimarca 25 €", punti=100,
             categoria="Gift card", consegna="codice via email, 2 gg lavorativi"),
        dict(id="carb50", emoji="⛽", nome="Buono carburante 50 €", punti=200,
             categoria="Gift card", consegna="codice via email, 2 gg lavorativi"),
        dict(id="gourmet", emoji="🧺", nome="Cesto gourmet regionale", punti=300,
             categoria="Casa & Gusto", consegna="corriere, 7 gg lavorativi"),
        dict(id="cuffie", emoji="🎧", nome="Cuffie noise cancelling", punti=450,
             categoria="Tecnologia", consegna="corriere, 5 gg lavorativi"),
        dict(id="watch", emoji="⌚", nome="Smartwatch sport", punti=700,
             categoria="Tecnologia", consegna="corriere, 5 gg lavorativi"),
        dict(id="spa", emoji="💆", nome="Weekend benessere per 2", punti=1200,
             categoria="Viaggi", consegna="voucher nominativo, validità 12 mesi"),
        dict(id="tv55", emoji="📺", nome="Smart TV 55\"", punti=2000,
             categoria="Tecnologia", consegna="corriere, 10 gg lavorativi"),
        dict(id="viaggio", emoji="✈️", nome="Viaggio capitali europee per 2", punti=3600,
             categoria="Viaggi", consegna="agenzia dedicata, date da concordare"),
    ]
    comunicazioni = [
        dict(data="2026-06-01", titolo="Acceleratore estivo attivo",
             testo="A giugno e luglio i climatizzatori valgono il 50% in più (art. 6.3)."),
        dict(data="2026-05-29", titolo="Novità dal 1° giugno: regolamento rivisto",
             testo="Cap mensile commodity a 900 punti e fotovoltaico a 200 punti (rev. 1 del regolamento, contratto v2)."),
        dict(data="2026-04-01", titolo="Spazio alla Meta 2026 è partita!",
             testo="6 mesi di gara, obiettivi mensili per cluster e classifica finale con premi extra."),
    ]

    stato = dict(
        gara=dict(nome="Spazio alla Meta 2026", codice="SAM2026",
                  periodo="2026-04-01 → 2026-09-30", data_riferimento=DATA_RIFERIMENTO,
                  giorni_rimanenti=GIORNI_RIMANENTI,
                  mese_corrente=f"{MESE_PARZIALE} (dati parziali al 07/06)",
                  contratto_attivo=2, tasso_eur_per_punto=tasso,
                  versioni_contratto=[
                      dict(v=1, valido_dal="2026-04-01", approvato_il="2026-03-27"),
                      dict(v=2, valido_dal="2026-06-01", approvato_il="2026-05-29",
                           changelog=[c["campo"] + f": {c['da']} → {c['a']}" for c in contratti[1]["changelog"]]),
                  ]),
        pv=stato_pv, classifiche=classifiche, riconciliazione=riconciliazione,
        whatif=whatif, alerts=alerts, approvazioni=approvazioni,
        catalogo=catalogo, comunicazioni=comunicazioni,
        compilazione=json.loads((CONTRATTI / "compilazione_report.json").read_text()),
        ledger_stats=dict(eventi=len(ledger), run_id=run_id,
                          contabilizzati=sum(1 for e in ledger if e["stato"] == "contabilizzato"),
                          in_approvazione=sum(1 for e in ledger if e["stato"] == "in_approvazione")))

    with open(OUTPUT / "state.json", "w") as f:
        json.dump(stato, f, ensure_ascii=False, indent=1)

    # ----- riepilogo e sanity check -------------------------------------------
    print(f"✓ Motore eseguito ({run_id})")
    print(f"  Eventi ledger: {len(ledger)} ({stato['ledger_stats']['contabilizzati']} contabilizzati, "
          f"{stato['ledger_stats']['in_approvazione']} in approvazione)")
    print(f"  Riconciliazione apr+mag: {riconciliazione['allineati']}/{riconciliazione['pv_totali']} allineati, "
          f"{riconciliazione['divergenze']} divergenze")
    for r in riconciliazione["righe"]:
        if r["esito"] == "KO":
            print(f"    KO {r['pv']}: Δ{r['delta']:+d} — {r['diagnosi']}")
    print(f"  Quarantena: {sorted(quarantena)}")
    print(f"  What-if v2 retroattiva: Δ{whatif['delta_punti_totale']:+d} punti "
          f"({whatif['delta_budget_eur']:+.2f} €) su {whatif['pv_impattati']} PV")
    attesi = dict(divergenze=2, quarantena=1)
    ok = riconciliazione["divergenze"] == attesi["divergenze"] and len(quarantena) == attesi["quarantena"]
    print("  Sanity check:", "OK ✓" if ok else f"ATTENZIONE: attesi {attesi}")


if __name__ == "__main__":
    main()
