#!/usr/bin/env python3
"""
REGOLO — API DI SERVING (L4) — il "backend headless".

Espone in lettura tutto ciò che qualunque frontend (il nuovo white-label, la
PIATTAFORMA legacy, una DEM, un export) deve poter consumare: saldi, movimenti,
progressi, classifiche, cataloghi, comunicazioni — più le viste di control
plane (riconciliazione, what-if, approvazioni, alert, report di compilazione).

L'API legge SOLO gli artefatti prodotti dal motore (output/state.json e
output/ledger.jsonl): non calcola nulla. Porta 8788 (la 8765 è di MAGI).
"""

import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

QUI = Path(__file__).parent
MOCKUP = QUI.parent
OUTPUT = MOCKUP / "output"
FRONTEND = MOCKUP / "05_frontend"

app = FastAPI(title="REGOLO — API di serving (mockup)", version="0.1")

_stato: dict = {}


def stato() -> dict:
    """Carica state.json (cache in memoria, ricaricabile con /api/reload)."""
    global _stato
    if not _stato:
        f = OUTPUT / "state.json"
        if not f.exists():
            raise HTTPException(503, "state.json mancante: eseguire prima mockup/03_motore/motore.py")
        _stato = json.loads(f.read_text())
    return _stato


# ----- frontend ------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/backoffice", include_in_schema=False)
def backoffice():
    return FileResponse(FRONTEND / "backoffice.html")


# ----- API utente finale (frontend L5) ---------------------------------------

@app.get("/api/gara")
def gara():
    return stato()["gara"]


@app.get("/api/pv")
def lista_pv():
    return [dict(codice=p["codice"], insegna=p["insegna"], cluster=p["cluster"])
            for p in sorted(stato()["pv"].values(), key=lambda x: x["codice"])]


@app.get("/api/pv/{codice}")
def dettaglio_pv(codice: str):
    pv = stato()["pv"].get(codice.upper())
    if not pv:
        raise HTTPException(404, f"PV {codice} non trovato")
    return pv


@app.get("/api/classifiche")
def classifiche():
    return stato()["classifiche"]


@app.get("/api/catalogo")
def catalogo():
    return stato()["catalogo"]


@app.get("/api/comunicazioni")
def comunicazioni():
    return stato()["comunicazioni"]


# ----- API control plane (backoffice L6) --------------------------------------

@app.get("/api/riconciliazione")
def riconciliazione():
    return stato()["riconciliazione"]


@app.get("/api/whatif")
def whatif():
    return stato()["whatif"]


@app.get("/api/alerts")
def alerts():
    return stato()["alerts"]


@app.get("/api/approvazioni")
def approvazioni():
    return stato()["approvazioni"]


@app.get("/api/compilazione")
def compilazione():
    return stato()["compilazione"]


@app.get("/api/compilazione_ai")
def compilazione_ai():
    """Report della compilazione AI REALE (se eseguita: mockup/01_contratto/compilatore.py)."""
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


@app.post("/api/reload")
def reload():
    global _stato
    _stato = {}
    return dict(esito="ok", nota="state.json verrà riletto alla prossima richiesta")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8788, log_level="warning")
