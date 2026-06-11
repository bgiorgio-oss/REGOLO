#!/usr/bin/env python3
"""
REGOLO — COMPILATORE DI REGOLAMENTI (L1) — v0, AI REALE.

Legge il regolamento (testo), chiama un LLM vero e produce:
  compilato_ai/gara_compilata_ai.yaml      il Contratto di Gara proposto dall'AI
  compilato_ai/compilazione_report_ai.json il report clausola per clausola (confidenze,
                                           escalation) + metadati del run (modello, token)
  compilato_ai/confronto_v1.json           auto-verifica: parametri estratti dall'AI vs
                                           contratto v1 approvato a mano (ground truth)

Provider (auto-detect): Gemini via Vertex AI ADC (come da .env) → fallback Ollama locale.
L'LLM lavora SOLO qui, a compile-time: il motore (L2) resta deterministico.

Uso:
  venv/bin/python mockup/01_contratto/compilatore.py
  venv/bin/python mockup/01_contratto/compilatore.py --regolamento altro.md --provider ollama
"""

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

import yaml

QUI = Path(__file__).parent
ROOT = QUI.parent.parent
REGOLAMENTO_DEFAULT = QUI.parent / "00_regolamento" / "REGOLAMENTO_SPAZIO_ALLA_META_2026.md"
OUT = QUI / "compilato_ai"
SOGLIA_CONFIDENZA = 0.80


def carica_env() -> dict:
    """Parser minimale del .env di progetto (niente dipendenze extra)."""
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for riga in f.read_text().splitlines():
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ---------------------------------------------------------------------------
# Prompt — schema astratto, con esempio generico (NESSUN numero della gara:
# il modello deve estrarre tutto dal regolamento, l'auto-verifica è a valle)
# ---------------------------------------------------------------------------

PROMPT = """Sei il Compilatore di Regolamenti di REGOLO, il sistema loyalty di H&A Motivation.
Trasformi il regolamento di un'operazione a premi in un "Contratto di Gara": una specifica
strutturata ed ESEGUIBILE da un motore di calcolo deterministico.

REGOLE TASSATIVE:
1. Estrai SOLO ciò che il regolamento dice. Non inventare valori, non "completare" regole.
2. Ogni elemento del contratto cita la clausola di origine in `fonte_clausola` (es. "art. 5.1").
3. Per ogni clausola interpretata compila una voce di report con `confidenza` (0.0–1.0).
4. Se una clausola è AMBIGUA: NON scegliere tu un'interpretazione. Metti
   `stato: "da_verificare"`, confidenza < 0.8, spiega il dubbio in `motivo_escalation`
   e aggiungi la voce anche in `contratto.clausole_da_verificare`.
4-bis. CHECKLIST AMBIGUITÀ — verificala voce per voce, è il tuo compito più importante
   (errori qui muovono denaro). Per OGNI clausola chiediti:
   a) finestre temporali ("entro N giorni/mesi"): la DECORRENZA è specificata
      (da firma? da attivazione? da caricamento dati?)? Se non lo è → da_verificare.
   b) bonus e premi: è ESPLICITO se sono una tantum o ricorrenti (per ogni mese/periodo)?
      Se il testo non lo dichiara → da_verificare.
   c) cap e massimali: è chiaro se si applicano al lordo o al netto degli storni?
   d) condizioni e formule: tutte le grandezze citate sono definite (netto/lordo,
      arrotondamenti, periodo di riferimento)?
   e) termini vaghi ("adeguato", "regolare", "può essere aggiornato"): hanno effetti
      sul calcolo? Se sì → da_verificare.
   Un'interpretazione "ragionevole ma non scritta" è un ERRORE, non un servizio.
5. Usa id in snake_case. Per i KPI usa nomi brevi derivati dal prodotto
   (es. luce_gas, fibra, fotovoltaico, wallbox, clima).
6. Date in formato ISO (YYYY-MM-DD), mesi come "YYYY-MM". Numeri come numeri, non stringhe.
7. Rispondi SOLO con un oggetto JSON valido, nessun testo fuori dal JSON.

STRUTTURA DEL JSON DI RISPOSTA (i valori dell'esempio sono FITTIZI e generici):
{
  "contratto": {
    "meta": {"gara": "...", "codice": "...", "contratto_versione": 1,
             "valido_dal": "YYYY-MM-DD", "valido_al": "YYYY-MM-DD"},
    "destinatari": {"tipo": "...", "requisiti": "...", "fonte_clausola": "..."},
    "cluster": {"criterio": "...", "fonte_clausola": "...",
      "definizioni": [{"id": "ALFA", "condizione": "...", "target_mensile_commodity": 99}]},
    "kpi": [{"id": "vendita_x", "descrizione": "..."}],
    "meccaniche": [
      {"id": "punti_vendita_x", "tipo": "punti_per_unita", "kpi": "vendita_x", "punti": 5,
       "cap_mensile_punti": 999, "fonte_clausola": "..."},
      {"id": "punti_y", "tipo": "punti_per_unita", "kpi": "y", "punti": 7,
       "moltiplicatori": [{"periodi": ["YYYY-MM"], "fattore": 2.0, "fonte_clausola": "..."}],
       "fonte_clausola": "..."},
      {"id": "storni", "tipo": "storno", "regola": "...", "fonte_clausola": "..."},
      {"id": "bonus_esempio", "tipo": "bonus_condizionale", "condizione": "...",
       "punti": 50, "ricorrenza": "per_mese", "liquidazione": "solo_mese_concluso",
       "fonte_clausola": "..."}
    ],
    "classifica_finale": {"ambito": "...", "indice": "...",
      "premi_punti_extra": [{"posizione": 1, "punti": 999}], "fonte_clausola": "..."},
    "valorizzazione": {"tasso_eur_per_punto": 0.5, "catalogo": "...",
      "accredito": "...", "fonte_clausola": "..."},
    "caricamenti": {"flusso_prestazioni": "...", "finestra_contestazioni_giorni": 99,
      "fonte_clausola": "..."},
    "clausole_da_verificare": [{"articolo": "...", "dubbio": "..."}]
  },
  "report": {
    "clausole": [
      {"id": "C01", "articolo": "art. X", "testo_estratto": "...",
       "interpretazione": "...", "campo_contratto": "...",
       "confidenza": 0.97, "stato": "auto"},
      {"id": "C02", "articolo": "art. Y", "testo_estratto": "...",
       "interpretazione": "AMBIGUO: ...", "campo_contratto": "...",
       "confidenza": 0.55, "stato": "da_verificare", "motivo_escalation": "..."}
    ]
  }
}

REGOLAMENTO DA COMPILARE:
----------------------------------------
{REGOLAMENTO}
----------------------------------------"""


# ---------------------------------------------------------------------------
# Provider LLM
# ---------------------------------------------------------------------------

def chiama_gemini(prompt: str, env: dict) -> tuple[str, dict]:
    from google import genai
    from google.genai import types
    client = genai.Client(vertexai=True, project=env["GOOGLE_CLOUD_PROJECT"],
                          location=env.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
    modello = env.get("REGOLO_MODEL", "gemini-2.5-flash")
    t0 = time.time()
    resp = client.models.generate_content(
        model=modello, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0,
                                           response_mime_type="application/json"))
    um = resp.usage_metadata
    meta = dict(provider="gemini-vertex", modello=modello, durata_s=round(time.time() - t0, 1),
                token_input=um.prompt_token_count, token_output=um.candidates_token_count)
    return resp.text, meta


def chiama_ollama(prompt: str, env: dict) -> tuple[str, dict]:
    modello = env.get("REGOLO_MODEL_OLLAMA", "llama3.1")
    corpo = json.dumps(dict(model=modello, prompt=prompt, stream=False, format="json",
                            options=dict(temperature=0))).encode()
    t0 = time.time()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        dati = json.loads(r.read())
    meta = dict(provider="ollama", modello=modello, durata_s=round(time.time() - t0, 1))
    return dati["response"], meta


def ollama_disponibile() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            return len(json.loads(r.read()).get("models", [])) > 0
    except Exception:
        return False


def estrai_json(testo: str) -> dict:
    """Tollerante alle fence ```json eventualmente aggiunte dal modello."""
    testo = testo.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", testo, re.DOTALL)
    if m:
        testo = m.group(1)
    return json.loads(testo)


# ---------------------------------------------------------------------------
# Auto-verifica: parametri AI vs contratto v1 approvato (ground truth)
# ---------------------------------------------------------------------------

# sinonimi di naming tra compilazioni diverse (l'AI può chiamare "commodity"
# ciò che il contratto approvato chiama "luce_gas"): il confronto è semantico
SINONIMI_KPI = {
    "luce_gas": ["luce_gas", "commodity", "luce", "gas"],
    "fibra": ["fibra"],
    "fotovoltaico": ["fotovoltaico", "fv"],
    "wallbox": ["wallbox", "juicebox"],
    "clima": ["clima", "climatizzatore", "condizionatore"],
}


def _mecc_per_kpi(contratto: dict, kpi: str) -> dict | None:
    nomi = SINONIMI_KPI.get(kpi, [kpi])
    for nome in nomi:
        for m in contratto.get("meccaniche", []):
            if m.get("kpi") == nome or nome in str(m.get("id", "")).lower():
                return m
    return None


def _bonus_con(contratto: dict, parole: list[str]) -> dict | None:
    for m in contratto.get("meccaniche", []):
        blob = (str(m.get("id", "")) + " " + str(m.get("condizione", ""))).lower()
        if "bonus" in (str(m.get("tipo", "")) + str(m.get("id", ""))).lower() \
           and all(p in blob for p in parole):
            return m
    return None


def _target_cluster(contratto: dict, cid: str):
    for d in contratto.get("cluster", {}).get("definizioni", []):
        if str(d.get("id", "")).upper() == cid:
            return d.get("target_mensile_commodity")
    return None


def estrai_parametri(c: dict) -> dict:
    """I parametri 'che muovono soldi': base del confronto AI vs approvato."""
    p = {}
    for kpi in ("luce_gas", "fibra", "fotovoltaico", "wallbox", "clima"):
        m = _mecc_per_kpi(c, kpi) or {}
        p[f"punti_{kpi}"] = m.get("punti")
    m_comm = _mecc_per_kpi(c, "luce_gas") or {}
    p["cap_commodity"] = m_comm.get("cap_mensile_punti")
    m_clima = _mecc_per_kpi(c, "clima") or {}
    molt = (m_clima.get("moltiplicatori") or [{}])[0]
    p["clima_moltiplicatore"] = molt.get("fattore")
    p["clima_mesi_moltiplicatore"] = sorted(str(x) for x in molt.get("periodi", [])) or None
    b_ob = _bonus_con(c, ["obiettivo"]) or _bonus_con(c, ["target"]) or {}
    p["bonus_obiettivo"] = b_ob.get("punti")
    b_tr = _bonus_con(c, ["fotovoltaico", "wallbox"]) or _bonus_con(c, ["tripletta"]) or {}
    p["bonus_tripletta"] = b_tr.get("punti")
    for cid in ("GOLD", "SILVER", "BRONZE"):
        p[f"target_{cid}"] = _target_cluster(c, cid)
    p["tasso_eur_per_punto"] = c.get("valorizzazione", {}).get("tasso_eur_per_punto")
    premi = c.get("classifica_finale", {}).get("premi_punti_extra", [])
    p["premi_classifica"] = sorted((x.get("punti") for x in premi), reverse=True) or None
    p["valido_dal"] = str(c.get("meta", {}).get("valido_dal", ""))[:10] or None
    p["valido_al"] = str(c.get("meta", {}).get("valido_al", ""))[:10] or None
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="REGOLO — Compilatore L1 (AI reale)")
    ap.add_argument("--regolamento", default=str(REGOLAMENTO_DEFAULT))
    ap.add_argument("--provider", choices=["auto", "gemini", "ollama"], default="auto")
    args = ap.parse_args()

    env = carica_env()
    testo = Path(args.regolamento).read_text()
    prompt = PROMPT.replace("{REGOLAMENTO}", testo)

    provider = args.provider
    if provider == "auto":
        adc = Path.home() / ".config/gcloud/application_default_credentials.json"
        if env.get("GOOGLE_CLOUD_PROJECT") and adc.exists():
            provider = "gemini"
        elif ollama_disponibile():
            provider = "ollama"
        else:
            raise SystemExit("Nessun provider LLM disponibile: configurare Vertex ADC nel .env "
                             "o avviare Ollama con un modello installato.")

    print(f"▸ Compilo «{Path(args.regolamento).name}» con provider: {provider}…")
    grezzo, meta = (chiama_gemini if provider == "gemini" else chiama_ollama)(prompt, env)
    risultato = estrai_json(grezzo)
    contratto, report = risultato["contratto"], risultato["report"]

    OUT.mkdir(exist_ok=True)
    (OUT / "raw_response.json").write_text(grezzo)
    with open(OUT / "gara_compilata_ai.yaml", "w") as f:
        f.write("# Contratto di Gara PROPOSTO DALL'AI — in attesa di review e approvazione umana.\n"
                f"# Generato da: {meta['provider']} / {meta['modello']} — NON usato dal motore\n"
                "# finché non viene approvato (HITL).\n")
        yaml.dump(contratto, f, allow_unicode=True, sort_keys=False)

    # escalation: clausole sotto soglia o marcate dal modello
    da_verificare = [c for c in report.get("clausole", [])
                     if c.get("stato") == "da_verificare" or c.get("confidenza", 1) < SOGLIA_CONFIDENZA]
    report_completo = dict(
        _descrizione="Report di compilazione PRODOTTO DALL'AI (L1 reale, v0)",
        documento_fonte=Path(args.regolamento).name, esecuzione=meta,
        soglia_confidenza=SOGLIA_CONFIDENZA,
        statistiche=dict(clausole_analizzate=len(report.get("clausole", [])),
                         escalation_verifica_umana=len(da_verificare)),
        clausole=report.get("clausole", []))
    (OUT / "compilazione_report_ai.json").write_text(
        json.dumps(report_completo, ensure_ascii=False, indent=1))

    # ----- auto-verifica vs contratto approvato -----------------------------
    with open(QUI / "gara_spazio_alla_meta.v1.yaml") as f:
        v1 = yaml.safe_load(f)
    p_v1, p_ai = estrai_parametri(v1), estrai_parametri(contratto)
    confronto = [dict(parametro=k, approvato_v1=p_v1[k], proposto_ai=p_ai.get(k),
                      esito="OK" if p_ai.get(k) == p_v1[k] else "DIFF") for k in p_v1]
    conformi = sum(1 for r in confronto if r["esito"] == "OK")
    (OUT / "confronto_v1.json").write_text(json.dumps(dict(
        descrizione="Auto-verifica: parametri della compilazione AI vs contratto v1 approvato",
        conformi=conformi, totale=len(confronto), esecuzione=meta,
        righe=confronto), ensure_ascii=False, indent=1))

    # ----- esito a console ----------------------------------------------------
    print(f"✓ Compilazione completata in {meta['durata_s']}s "
          f"({meta.get('token_input', '?')} token in / {meta.get('token_output', '?')} out)")
    print(f"\n  AUTO-VERIFICA — parametri vs contratto v1 approvato: {conformi}/{len(confronto)} conformi")
    for r in confronto:
        segno = "✓" if r["esito"] == "OK" else "✗"
        extra = "" if r["esito"] == "OK" else f"   (AI: {r['proposto_ai']} | v1: {r['approvato_v1']})"
        print(f"   {segno} {r['parametro']}{extra}")
    print(f"\n  ESCALATION A VERIFICA UMANA: {len(da_verificare)} clausole")
    for c in da_verificare:
        print(f"   ⚠ {c.get('articolo', '?')} (conf. {c.get('confidenza', '?')}): "
              f"{c.get('motivo_escalation') or c.get('interpretazione', '')[:110]}")
    print(f"\n  Output in {OUT.relative_to(ROOT)}/ — il contratto AI NON sostituisce il v1")
    print("  approvato: nel sistema reale passerebbe ora dalla review umana (HITL).")


if __name__ == "__main__":
    main()
