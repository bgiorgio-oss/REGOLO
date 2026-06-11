#!/usr/bin/env python3
"""
REGOLO — API DI SERVING (L4) — il "backend headless".

v2: oltre alle letture, espone AZIONI REALI che persistono in output/runtime.json:
  - ordini a catalogo (spesa del credito, con controllo saldo)
  - ticket del contact center (apertura lato PV, risposta lato backoffice)
  - approvazione HITL del batch credito (sposta giugno: in_approvazione → contabilizzato)
  - pubblicazione comunicazioni
  - upload file prestazioni con validazione (schema, codici, anomalie) — anteprima
  - risoluzione alert qualità dati

Separazione netta: ciò che CALCOLA il motore sta in state.json/ledger.jsonl (sola lettura
qui); ciò che FANNO gli utenti sta in runtime.json. L'API compone le due viste.
Porta 8788 (la 8765 è di MAGI). Reset demo: POST /api/reset_demo.
"""

import copy
import csv
import io
import json
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

QUI = Path(__file__).parent
MOCKUP = QUI.parent
OUTPUT = MOCKUP / "output"
FRONTEND = MOCKUP / "05_frontend"
RUNTIME_F = OUTPUT / "runtime.json"

app = FastAPI(title="REGOLO — API di serving (mockup)", version="0.2")

_stato: dict = {}

SOGLIA_ANOMALIA = 5  # stessa soglia del motore: input > 5x media storica → anomalia
COLONNE_PRESTAZIONI = ["periodo", "codice_pv", "luce_gas", "fibra", "fotovoltaico",
                       "wallbox", "clima", "storni_luce_gas", "storni_fibra"]

SEED_RUNTIME = dict(
    contatori=dict(ordine=1, ticket=2),
    ordini=[dict(id="ORD-0001", pv="SE-RM-001", premio_id="carb50",
                 premio="Buono carburante 50 €", punti=200, stato="spedito",
                 ts="2026-06-05 11:32")],
    tickets=[
        dict(id="TCK-0001", pv="SE-BO-001", categoria="Contestazione punteggio",
             oggetto="Storno di aprile non riconosciuto",
             messaggio="Buongiorno, ad aprile mi risulta uno storno di 2 contratti ma i "
                       "clienti non hanno mai receduto. Chiedo verifica (art. 9.2).",
             riferimento="EV su periodo 2026-04", stato="aperto",
             ts="2026-06-09 09:15", risposte=[]),
        dict(id="TCK-0002", pv="SE-CT-001", categoria="Premi e catalogo",
             oggetto="Tempi di consegna Smart TV",
             messaggio="Ho richiesto la Smart TV 55\": quali sono i tempi di consegna?",
             riferimento=None, stato="risposto", ts="2026-06-03 16:40",
             risposte=[dict(da="Contact center", ts="2026-06-04 10:02",
                            testo="Buongiorno! La consegna avviene via corriere entro 10 "
                                  "giorni lavorativi dalla validazione dell'ordine.")]),
    ],
    approvazioni={}, alerts_risolti={}, comunicazioni_extra=[], caricamenti=[])


# ---------------------------------------------------------------------------
# Stato (motore, sola lettura) + runtime (azioni utenti, lettura/scrittura)
# ---------------------------------------------------------------------------

def stato() -> dict:
    global _stato
    if not _stato:
        f = OUTPUT / "state.json"
        if not f.exists():
            raise HTTPException(503, "state.json mancante: eseguire prima mockup/03_motore/motore.py")
        _stato = json.loads(f.read_text())
    return _stato


def runtime() -> dict:
    if not RUNTIME_F.exists():
        RUNTIME_F.parent.mkdir(exist_ok=True)
        RUNTIME_F.write_text(json.dumps(SEED_RUNTIME, ensure_ascii=False, indent=1))
    return json.loads(RUNTIME_F.read_text())


def salva_runtime(rt: dict) -> None:
    RUNTIME_F.write_text(json.dumps(rt, ensure_ascii=False, indent=1))


def adesso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def nuovo_id(rt: dict, tipo: str, prefisso: str) -> str:
    rt["contatori"][tipo] = rt["contatori"].get(tipo, 0) + 1
    return f"{prefisso}-{rt['contatori'][tipo]:04d}"


# ---------------------------------------------------------------------------
# Vista PV composta: stato del motore + overlay runtime
# ---------------------------------------------------------------------------

def vista_pv(codice: str, rt: dict) -> dict:
    base = stato()["pv"].get(codice.upper())
    if not base:
        raise HTTPException(404, f"PV {codice} non trovato")
    pv = copy.deepcopy(base)

    # 1. approvazione batch giugno (HITL): sposta l'in_approvazione nel contabilizzato
    appr = rt["approvazioni"].get("giugno_2026")
    if appr:
        pv["saldo_contabilizzato"] += pv["saldo_in_approvazione"]
        pv["saldo_in_approvazione"] = 0
        for m in pv["movimenti"]:
            if m["stato"] == "in_approvazione":
                m["stato"] = "contabilizzato"

    # 2. ordini (spesa del credito) come movimenti negativi
    ordini = [o for o in rt["ordini"] if o["pv"] == codice.upper()]
    spesa = sum(o["punti"] for o in ordini)
    for o in sorted(ordini, key=lambda x: x["ts"], reverse=True):
        pv["movimenti"].insert(0, dict(
            id=o["id"], ts=o["ts"], gara="SAM2026", pv=o["pv"], periodo=o["ts"][:7],
            tipo="spesa", meccanica="catalogo", punti=-o["punti"],
            descrizione=f"Richiesta premio: {o['premio']}", contratto_v="-",
            run_id="runtime", stato="contabilizzato"))

    pv["spesa_totale"] = spesa
    pv["saldo_disponibile"] = pv["saldo_contabilizzato"] - spesa
    tasso = stato()["gara"]["tasso_eur_per_punto"]
    pv["valore_eur"] = round(pv["saldo_disponibile"] * tasso, 2)
    pv["ordini"] = sorted(ordini, key=lambda x: x["ts"], reverse=True)
    pv["tickets"] = sorted([t for t in rt["tickets"] if t["pv"] == codice.upper()],
                           key=lambda x: x["ts"], reverse=True)
    return pv


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/backoffice", include_in_schema=False)
def backoffice():
    return FileResponse(FRONTEND / "backoffice.html")


# ---------------------------------------------------------------------------
# Letture
# ---------------------------------------------------------------------------

@app.get("/api/gara")
def gara():
    return stato()["gara"]


@app.get("/api/pv")
def lista_pv():
    return [dict(codice=p["codice"], insegna=p["insegna"], cluster=p["cluster"])
            for p in sorted(stato()["pv"].values(), key=lambda x: x["codice"])]


@app.get("/api/pv/{codice}")
def dettaglio_pv(codice: str):
    return vista_pv(codice, runtime())


@app.get("/api/anagrafica")
def anagrafica():
    rt = runtime()
    out = []
    for p in sorted(stato()["pv"].values(), key=lambda x: x["codice"]):
        v = vista_pv(p["codice"], rt)
        out.append({k: v[k] for k in ("codice", "insegna", "citta", "provincia", "regione",
                                      "cluster", "email", "media_2025", "data_adesione",
                                      "stato_pv", "saldo_disponibile", "posizione_classifica")})
    return out


@app.get("/api/classifiche")
def classifiche():
    return stato()["classifiche"]


@app.get("/api/catalogo")
def catalogo():
    return stato()["catalogo"]


@app.get("/api/comunicazioni")
def comunicazioni():
    rt = runtime()
    return sorted(rt["comunicazioni_extra"] + stato()["comunicazioni"],
                  key=lambda c: c["data"], reverse=True)


@app.get("/api/riconciliazione")
def riconciliazione():
    return stato()["riconciliazione"]


@app.get("/api/whatif")
def whatif():
    return stato()["whatif"]


@app.get("/api/alerts")
def alerts():
    rt = runtime()
    out = copy.deepcopy(stato()["alerts"])
    for a in out:
        ris = rt["alerts_risolti"].get(a["pv"])
        if ris:
            a["stato"] = "risolto"
            a["risoluzione"] = ris
    return out


@app.get("/api/approvazioni")
def approvazioni():
    rt = runtime()
    out = copy.deepcopy(stato()["approvazioni"])
    appr = rt["approvazioni"].get("giugno_2026")
    for a in out:
        if a["stato"] == "in_attesa" and appr:
            a.update(stato="approvato", approvato_da=appr["approvato_da"],
                     approvato_il=appr["ts"])
    return out


@app.get("/api/compilazione")
def compilazione():
    return stato()["compilazione"]


@app.get("/api/compilazione_ai")
def compilazione_ai():
    base = MOCKUP / "01_contratto" / "compilato_ai"
    rep = base / "compilazione_report_ai.json"
    if not rep.exists():
        raise HTTPException(404, "compilazione AI non ancora eseguita")
    out = json.loads(rep.read_text())
    confronto = base / "confronto_v1.json"
    if confronto.exists():
        out["confronto_v1"] = json.loads(confronto.read_text())
    return out


@app.get("/api/ledger")
def ledger(pv: str | None = None, limit: int = 100):
    f = OUTPUT / "ledger.jsonl"
    if not f.exists():
        raise HTTPException(503, "ledger.jsonl mancante: eseguire prima il motore")
    eventi = [json.loads(r) for r in f.read_text().splitlines()]
    if pv:
        eventi = [e for e in eventi if e["pv"] == pv.upper()]
    return dict(totale=len(eventi), eventi=eventi[::-1][:limit])


@app.get("/api/tickets")
def tutti_i_tickets():
    return sorted(runtime()["tickets"], key=lambda t: t["ts"], reverse=True)


@app.get("/api/ordini")
def tutti_gli_ordini():
    return sorted(runtime()["ordini"], key=lambda o: o["ts"], reverse=True)


@app.get("/api/caricamenti")
def storico_caricamenti():
    """Storico: i 3 flussi del mockup + gli upload validati a runtime."""
    storici = [
        dict(file="prestazioni_2026-04.csv", ts="2026-05-04 08:55", righe=25, esito="ok",
             nota="caricato e contabilizzato (batch aprile)"),
        dict(file="prestazioni_2026-05.csv", ts="2026-06-04 08:40", righe=25, esito="ok",
             nota="caricato e contabilizzato (batch maggio)"),
        dict(file="prestazioni_2026-06.csv", ts="2026-06-08 09:00", righe=25, esito="con_anomalie",
             nota="parziale al 07/06 — 1 PV in quarantena (SE-RM-003), batch in approvazione"),
    ]
    return storici + runtime()["caricamenti"]


# ---------------------------------------------------------------------------
# Azioni (scrivono nel runtime)
# ---------------------------------------------------------------------------

class OrdineReq(BaseModel):
    premio_id: str


@app.post("/api/pv/{codice}/ordini")
def crea_ordine(codice: str, req: OrdineReq):
    rt = runtime()
    premio = next((p for p in stato()["catalogo"] if p["id"] == req.premio_id), None)
    if not premio:
        raise HTTPException(404, "premio non trovato")
    pv = vista_pv(codice, rt)
    if pv["saldo_disponibile"] < premio["punti"]:
        raise HTTPException(409, f"saldo insufficiente: disponibili {pv['saldo_disponibile']} punti, "
                                 f"richiesti {premio['punti']}")
    ordine = dict(id=nuovo_id(rt, "ordine", "ORD"), pv=codice.upper(),
                  premio_id=premio["id"], premio=premio["nome"], punti=premio["punti"],
                  stato="richiesto", ts=adesso())
    rt["ordini"].append(ordine)
    salva_runtime(rt)
    return dict(esito="ok", ordine=ordine,
                saldo_disponibile=pv["saldo_disponibile"] - premio["punti"])


class TicketReq(BaseModel):
    categoria: str
    oggetto: str
    messaggio: str
    riferimento: str | None = None


@app.post("/api/pv/{codice}/tickets")
def apri_ticket(codice: str, req: TicketReq):
    rt = runtime()
    if codice.upper() not in stato()["pv"]:
        raise HTTPException(404, f"PV {codice} non trovato")
    ticket = dict(id=nuovo_id(rt, "ticket", "TCK"), pv=codice.upper(),
                  categoria=req.categoria, oggetto=req.oggetto, messaggio=req.messaggio,
                  riferimento=req.riferimento, stato="aperto", ts=adesso(), risposte=[])
    rt["tickets"].append(ticket)
    salva_runtime(rt)
    return dict(esito="ok", ticket=ticket)


class RispostaReq(BaseModel):
    testo: str
    chiudi: bool = True


@app.post("/api/tickets/{ticket_id}/rispondi")
def rispondi_ticket(ticket_id: str, req: RispostaReq):
    rt = runtime()
    t = next((t for t in rt["tickets"] if t["id"] == ticket_id), None)
    if not t:
        raise HTTPException(404, "ticket non trovato")
    t["risposte"].append(dict(da="Contact center", testo=req.testo, ts=adesso()))
    t["stato"] = "risposto" if req.chiudi else "in_lavorazione"
    salva_runtime(rt)
    return dict(esito="ok", ticket=t)


class ApprovaReq(BaseModel):
    approvato_da: str = "operations"


@app.post("/api/approvazioni/giugno/approva")
def approva_giugno(req: ApprovaReq):
    rt = runtime()
    if rt["approvazioni"].get("giugno_2026"):
        raise HTTPException(409, "batch già approvato")
    rt["approvazioni"]["giugno_2026"] = dict(approvato_da=req.approvato_da, ts=adesso())
    salva_runtime(rt)
    batch = next(a for a in stato()["approvazioni"] if a["stato"] == "in_attesa")
    return dict(esito="ok", batch=batch["batch"], punti=batch["punti"],
                nota="eventi di giugno contabilizzati: i saldi dei PV sono aggiornati")


class NotaReq(BaseModel):
    nota: str = ""


@app.post("/api/alerts/{pv}/risolvi")
def risolvi_alert(pv: str, req: NotaReq):
    rt = runtime()
    if not any(a["pv"] == pv.upper() for a in stato()["alerts"]):
        raise HTTPException(404, "alert non trovato")
    rt["alerts_risolti"][pv.upper()] = dict(
        nota=req.nota or "verificato col Promotore", ts=adesso())
    salva_runtime(rt)
    return dict(esito="ok")


class ComunicazioneReq(BaseModel):
    titolo: str
    testo: str


@app.post("/api/comunicazioni")
def pubblica_comunicazione(req: ComunicazioneReq):
    rt = runtime()
    com = dict(data=adesso()[:10], titolo=req.titolo, testo=req.testo, runtime=True)
    rt["comunicazioni_extra"].insert(0, com)
    salva_runtime(rt)
    return dict(esito="ok", comunicazione=com)


@app.post("/api/caricamenti")
async def valida_caricamento(file: UploadFile = File(...)):
    """Validazione di un flusso prestazioni: schema, codici PV, valori, anomalie.
    Anteprima realistica del flusso B (il mockup non ricalcola: serve il motore)."""
    contenuto = (await file.read()).decode("utf-8", errors="replace")
    try:
        righe = list(csv.DictReader(io.StringIO(contenuto)))
    except Exception:
        raise HTTPException(400, "file non leggibile come CSV")

    errori, anomalie = [], []
    intestazione = list(righe[0].keys()) if righe else []
    if intestazione != COLONNE_PRESTAZIONI:
        errori.append(f"intestazione attesa {COLONNE_PRESTAZIONI}, trovata {intestazione}")

    pv_noti = set(stato()["pv"].keys())
    tot_attivazioni, pv_visti = 0, set()
    if not errori:
        for i, r in enumerate(righe, 2):  # riga 1 = header
            cod = r.get("codice_pv", "")
            if cod not in pv_noti:
                errori.append(f"riga {i}: codice PV sconosciuto «{cod}»")
                continue
            try:
                valori = {k: int(r[k]) for k in COLONNE_PRESTAZIONI[2:]}
            except (ValueError, KeyError):
                errori.append(f"riga {i}: valori non numerici")
                continue
            if any(v < 0 for v in valori.values()):
                errori.append(f"riga {i}: valori negativi")
                continue
            pv_visti.add(cod)
            tot_attivazioni += valori["luce_gas"]
            # anomalia vs storico (stessa logica del motore)
            mesi = stato()["pv"][cod]["mesi"]
            storico = [m["attivazioni_nette"] for m in mesi if not m["parziale"]]
            media = sum(storico) / len(storico) if storico else 0
            soglia = SOGLIA_ANOMALIA * max(media, 5)
            if valori["luce_gas"] > soglia:
                anomalie.append(f"{cod}: luce_gas={valori['luce_gas']} vs media storica "
                                f"{media:.0f} (soglia {soglia:.0f}) → andrebbe in QUARANTENA")

    esito = "respinto" if errori else ("con_anomalie" if anomalie else "ok")
    report = dict(file=file.filename, ts=adesso(), righe=len(righe),
                  pv_coinvolti=len(pv_visti), totale_attivazioni=tot_attivazioni,
                  errori=errori[:10], anomalie=anomalie[:10], esito=esito,
                  nota="validazione di anteprima — nel flusso reale seguirebbe il run del motore")
    rt = runtime()
    rt["caricamenti"].insert(0, report)
    salva_runtime(rt)
    return report


@app.post("/api/reset_demo")
def reset_demo():
    """Riporta la demo allo stato iniziale (azzera ordini/ticket/approvazioni runtime)."""
    if RUNTIME_F.exists():
        RUNTIME_F.unlink()
    return dict(esito="ok", nota="runtime azzerato e ri-inizializzato col seed demo")


@app.post("/api/reload")
def reload():
    global _stato
    _stato = {}
    return dict(esito="ok", nota="state.json verrà riletto alla prossima richiesta")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8788, log_level="warning")
