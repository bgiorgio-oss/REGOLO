#!/usr/bin/env python3
"""
SPIKE — Structured output con schema Pydantic per il Compilatore L1.

Domanda: conviene sostituire il parsing JSON manuale del compilatore con uno
schema Pydantic validato? E con quale strada?
  A) NATIVA: google-genai `response_schema=<modello Pydantic>` + retry manuale
     sugli errori di validazione
  B) INSTRUCTOR: `instructor.from_genai(...)` con `max_retries` automatici

Metodo: stesso prompt (regole + checklist ambiguità, SENZA descrivere la
struttura JSON: la struttura arriva dallo schema), stesso modello
(gemini-2.5-flash via Vertex ADC), stessa auto-verifica dei parametri contro
il contratto v1 approvato a mano (ground truth) usata negli spike precedenti.
"""

import importlib.util
import json
import time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

QUI = Path(__file__).parent
ROOT = QUI.parent.parent
CONTRATTI = ROOT / "mockup" / "01_contratto"
REGOLAMENTO = ROOT / "mockup" / "00_regolamento" / "REGOLAMENTO_SPAZIO_ALLA_META_2026.md"

# riusa carica_env() ed estrai_parametri() del compilatore del mockup
spec = importlib.util.spec_from_file_location("compilatore", CONTRATTI / "compilatore.py")
compilatore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compilatore)


# ---------------------------------------------------------------------------
# Lo schema Pydantic del Contratto di Gara — QUESTA è la novità dello spike:
# la struttura non vive più nel prompt ma in modelli tipizzati e validati.
# ---------------------------------------------------------------------------

class Moltiplicatore(BaseModel):
    periodi: list[str] = Field(description="mesi in formato YYYY-MM in cui vale il fattore")
    fattore: float
    fonte_clausola: str


class Meccanica(BaseModel):
    id: str = Field(description="snake_case; per i KPI usare luce_gas, fibra, fotovoltaico, wallbox, clima")
    tipo: Literal["punti_per_unita", "storno", "bonus_condizionale"]
    fonte_clausola: str
    kpi: str | None = None
    punti: float | None = Field(None, description="punti per unità o importo del bonus")
    cap_mensile_punti: int | None = None
    moltiplicatori: list[Moltiplicatore] | None = None
    condizione: str | None = Field(None, description="per i bonus: condizione leggibile e verificabile")
    ricorrenza: str | None = None
    liquidazione: str | None = None
    regola: str | None = Field(None, description="per gli storni: regola completa con decorrenza")


class ClusterDef(BaseModel):
    id: str
    condizione: str
    target_mensile_commodity: int


class Cluster(BaseModel):
    criterio: str
    fonte_clausola: str
    definizioni: list[ClusterDef]


class Kpi(BaseModel):
    id: str
    descrizione: str


class PremioClassifica(BaseModel):
    posizione: int
    punti: int


class ClassificaFinale(BaseModel):
    ambito: str
    indice: str
    premi_punti_extra: list[PremioClassifica]
    fonte_clausola: str


class Valorizzazione(BaseModel):
    tasso_eur_per_punto: float
    catalogo: str
    accredito: str
    fonte_clausola: str


class Caricamenti(BaseModel):
    flusso_prestazioni: str
    finestra_contestazioni_giorni: int
    fonte_clausola: str


class Meta(BaseModel):
    gara: str
    codice: str
    contratto_versione: int = 1
    valido_dal: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    valido_al: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class Destinatari(BaseModel):
    tipo: str
    requisiti: str
    fonte_clausola: str


class ClausolaDaVerificare(BaseModel):
    articolo: str
    dubbio: str


class Contratto(BaseModel):
    meta: Meta
    destinatari: Destinatari
    cluster: Cluster
    kpi: list[Kpi]
    meccaniche: list[Meccanica]
    classifica_finale: ClassificaFinale
    valorizzazione: Valorizzazione
    caricamenti: Caricamenti
    clausole_da_verificare: list[ClausolaDaVerificare] = []


class ClausolaReport(BaseModel):
    id: str
    articolo: str
    testo_estratto: str
    interpretazione: str
    campo_contratto: str
    confidenza: float = Field(ge=0.0, le=1.0)
    stato: Literal["auto", "da_verificare"]
    motivo_escalation: str | None = None

    @model_validator(mode="after")
    def coerenza_stato(self):
        # regola di business: sotto soglia non si interpreta d'ufficio
        if self.confidenza < 0.8 and self.stato == "auto":
            self.stato = "da_verificare"
        return self


class VoceChecklist(BaseModel):
    """Esito di UN controllo della checklist ambiguità, applicato a tutto il regolamento."""
    controllo: Literal["decorrenze_finestre_temporali", "ricorrenza_bonus",
                       "cap_lordo_o_netto", "grandezze_definite", "termini_vaghi"]
    esito: Literal["ok", "ambiguita_trovata"]
    dettaglio: str = Field(description="quali articoli sono stati controllati e cosa si è concluso; "
                                       "se ambiguità: articolo e natura del dubbio")


class Compilazione(BaseModel):
    """Output completo del Compilatore: contratto eseguibile + report clausola per clausola.
    La checklist_ambiguita è OBBLIGATORIA: una voce per ciascuno dei 5 controlli."""
    checklist_ambiguita: list[VoceChecklist] = Field(
        description="compilare PRIMA del contratto: i 5 controlli della checklist, uno per uno")
    contratto: Contratto
    report: list[ClausolaReport]

    @field_validator("report")
    @classmethod
    def report_non_vuoto(cls, v):
        if len(v) < 8:
            raise ValueError("il report deve coprire tutte le clausole rilevanti (almeno 8)")
        return v

    @field_validator("checklist_ambiguita")
    @classmethod
    def checklist_completa(cls, v):
        if {x.controllo for x in v} != {"decorrenze_finestre_temporali", "ricorrenza_bonus",
                                        "cap_lordo_o_netto", "grandezze_definite", "termini_vaghi"}:
            raise ValueError("la checklist deve contenere tutti e 5 i controlli, una voce ciascuno")
        return v

    @model_validator(mode="after")
    def ambiguita_coerenti(self):
        # se la checklist trova ambiguità, devono esserci escalation corrispondenti
        trovate = [x for x in self.checklist_ambiguita if x.esito == "ambiguita_trovata"]
        escalate = [c for c in self.report if c.stato == "da_verificare"]
        if trovate and not escalate:
            raise ValueError("la checklist segnala ambiguità ma nessuna clausola del report "
                             "è in stato da_verificare: incoerente")
        return self


# ---------------------------------------------------------------------------
# Prompt: SOLO le regole — la struttura la impone lo schema
# ---------------------------------------------------------------------------

PROMPT = """Sei il Compilatore di Regolamenti di REGOLO (sistema loyalty H&A Motivation).
Trasformi il regolamento di un'operazione a premi in un Contratto di Gara eseguibile.

REGOLE TASSATIVE:
1. Estrai SOLO ciò che il regolamento dice: non inventare né "completare" valori.
2. Ogni elemento cita la clausola di origine in fonte_clausola (es. "art. 5.1").
3. Per ogni clausola interpretata, una voce di report con confidenza 0.0-1.0.
4. CHECKLIST AMBIGUITÀ (il tuo compito più importante — errori qui muovono denaro):
   a) finestre temporali ("entro N giorni"): la DECORRENZA è specificata? Se no → da_verificare.
   b) bonus: è ESPLICITO se una tantum o ricorrenti? Se no → da_verificare.
   c) cap/massimali: lordo o netto degli storni?
   d) formule: tutte le grandezze citate sono definite?
   e) termini vaghi con effetti sul calcolo → da_verificare.
   Una clausola ambigua va in stato "da_verificare" con motivo_escalation e in
   contratto.clausole_da_verificare. Un'interpretazione "ragionevole ma non
   scritta" è un ERRORE, non un servizio.
5. Date ISO (YYYY-MM-DD), mesi "YYYY-MM", numeri come numeri.

REGOLAMENTO DA COMPILARE:
----------------------------------------
{REGOLAMENTO}
----------------------------------------"""


# ---------------------------------------------------------------------------
# Le due strade
# ---------------------------------------------------------------------------

def via_nativa(prompt: str, env: dict, max_tentativi: int = 3):
    """google-genai con response_schema Pydantic + retry manuale sugli errori."""
    from google import genai
    from google.genai import types
    client = genai.Client(vertexai=True, project=env["GOOGLE_CLOUD_PROJECT"],
                          location=env.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
    modello = env.get("REGOLO_MODEL", "gemini-2.5-flash")
    contents, errori = prompt, []
    for tentativo in range(1, max_tentativi + 1):
        t0 = time.time()
        resp = client.models.generate_content(
            model=modello, contents=contents,
            config=types.GenerateContentConfig(temperature=0.0,
                                               response_mime_type="application/json",
                                               response_schema=Compilazione))
        durata = time.time() - t0
        try:
            ris = resp.parsed if isinstance(resp.parsed, Compilazione) \
                else Compilazione.model_validate_json(resp.text)
            um = resp.usage_metadata
            return ris, dict(via="nativa (response_schema)", modello=modello,
                             tentativi=tentativo, durata_s=round(durata, 1),
                             token_input=um.prompt_token_count,
                             token_output=um.candidates_token_count)
        except Exception as e:
            errori.append(str(e)[:300])
            contents = (prompt + "\n\nIl tuo output precedente NON ha superato la validazione "
                        f"dello schema. Errori:\n{errori[-1]}\nCorreggi e riprova.")
    raise RuntimeError(f"validazione fallita dopo {max_tentativi} tentativi: {errori}")


def via_instructor(prompt: str, env: dict):
    """instructor.from_genai: retry-on-validation automatici."""
    import instructor
    from google import genai
    gclient = genai.Client(vertexai=True, project=env["GOOGLE_CLOUD_PROJECT"],
                           location=env.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
    client = instructor.from_genai(gclient)
    modello = env.get("REGOLO_MODEL", "gemini-2.5-flash")
    t0 = time.time()
    ris, raw = client.chat.completions.create_with_completion(
        model=modello,
        messages=[{"role": "user", "content": prompt}],
        response_model=Compilazione,
        max_retries=2)
    um = getattr(raw, "usage_metadata", None)
    return ris, dict(via="instructor (from_genai)", modello=modello,
                     durata_s=round(time.time() - t0, 1),
                     token_input=getattr(um, "prompt_token_count", "?"),
                     token_output=getattr(um, "candidates_token_count", "?"))


# ---------------------------------------------------------------------------
# Verifica e confronto
# ---------------------------------------------------------------------------

def verifica(ris: Compilazione, meta: dict, etichetta: str) -> dict:
    with open(CONTRATTI / "gara_spazio_alla_meta.v1.yaml") as f:
        v1 = yaml.safe_load(f)
    p_v1 = compilatore.estrai_parametri(v1)
    p_ai = compilatore.estrai_parametri(ris.contratto.model_dump())
    conformi = sum(1 for k in p_v1 if p_ai.get(k) == p_v1[k])
    diff = [k for k in p_v1 if p_ai.get(k) != p_v1[k]]
    escal = [c for c in ris.report if c.stato == "da_verificare"]

    with open(QUI / f"contratto_{etichetta}.yaml", "w") as f:
        f.write(f"# Contratto proposto — spike structured output, via {meta['via']}\n")
        yaml.dump(ris.contratto.model_dump(exclude_none=True), f,
                  allow_unicode=True, sort_keys=False)

    print(f"\n— {meta['via']} —")
    print(f"  {meta['durata_s']}s · tentativi/retry: {meta.get('tentativi', 'auto')} · "
          f"token {meta['token_input']}/{meta['token_output']}")
    print(f"  Parametri conformi al v1 approvato: {conformi}/{len(p_v1)}"
          + (f"  (diff: {', '.join(diff)})" if diff else ""))
    print(f"  Clausole nel report: {len(ris.report)} · escalation: {len(escal)}")
    for c in escal:
        print(f"    ⚠ {c.articolo} (conf. {c.confidenza}): "
              f"{(c.motivo_escalation or c.interpretazione)[:100]}")
    return dict(via=meta["via"], conformi=f"{conformi}/{len(p_v1)}",
                escalation=[c.articolo for c in escal], meta=meta)


def main() -> None:
    env = compilatore.carica_env()
    prompt = PROMPT.replace("{REGOLAMENTO}", REGOLAMENTO.read_text())
    esiti = []

    print("▸ Via A — google-genai nativa (response_schema Pydantic)…")
    try:
        ris, meta = via_nativa(prompt, env)
        esiti.append(verifica(ris, meta, "nativo"))
    except Exception as e:
        print("  ✗ FALLITA:", str(e)[:300]); esiti.append(dict(via="nativa", errore=str(e)[:300]))

    print("\n▸ Via B — instructor.from_genai (retry automatici)…")
    try:
        ris, meta = via_instructor(prompt, env)
        esiti.append(verifica(ris, meta, "instructor"))
    except Exception as e:
        print("  ✗ FALLITA:", str(e)[:300]); esiti.append(dict(via="instructor", errore=str(e)[:300]))

    (QUI / "esiti.json").write_text(json.dumps(esiti, ensure_ascii=False, indent=1))
    print("\n✓ Spike completato — esiti in spikes/instructor/esiti.json")


if __name__ == "__main__":
    main()
