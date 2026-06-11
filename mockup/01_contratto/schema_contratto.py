"""
REGOLO — Schema Pydantic del Contratto di Gara e del report di compilazione.

È LA fonte della struttura: il compilatore non descrive più il JSON nel prompt,
lo impone con questi modelli (via instructor) e li valida — incluse le regole
di business (confidenza ∈ [0,1], coerenza checklist↔escalation, date ISO).

Validato dallo spike `spikes/instructor/` (2026-06-11): con instructor il modello
mantiene il comportamento riflessivo sulle ambiguità (17/17 parametri + escalation
art. 5.7), mentre il constrained decoding nativo lo sopprime.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SOGLIA_CONFIDENZA = 0.80

CONTROLLI_CHECKLIST = ("decorrenze_finestre_temporali", "ricorrenza_bonus",
                       "cap_lordo_o_netto", "grandezze_definite", "termini_vaghi")


class Moltiplicatore(BaseModel):
    periodi: list[str] = Field(description="mesi YYYY-MM in cui vale il fattore")
    fattore: float
    fonte_clausola: str


class Meccanica(BaseModel):
    id: str = Field(description="snake_case; per i KPI usare nomi brevi tipo luce_gas, fibra, fotovoltaico, wallbox, clima")
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
        if self.confidenza < SOGLIA_CONFIDENZA and self.stato == "auto":
            self.stato = "da_verificare"
        return self


class VoceChecklist(BaseModel):
    """Esito di UN controllo della checklist ambiguità su tutto il regolamento."""
    controllo: Literal["decorrenze_finestre_temporali", "ricorrenza_bonus",
                       "cap_lordo_o_netto", "grandezze_definite", "termini_vaghi"]
    esito: Literal["ok", "ambiguita_trovata"]
    dettaglio: str = Field(description="articoli controllati e conclusione; se ambiguità: articolo e dubbio")


class Compilazione(BaseModel):
    """Output completo del Compilatore: checklist + contratto eseguibile + report."""
    checklist_ambiguita: list[VoceChecklist] = Field(
        description="compilare PRIMA del contratto: i 5 controlli, uno per voce")
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
        if {x.controllo for x in v} != set(CONTROLLI_CHECKLIST):
            raise ValueError("la checklist deve contenere tutti e 5 i controlli, una voce ciascuno")
        return v

    @model_validator(mode="after")
    def ambiguita_coerenti(self):
        trovate = [x for x in self.checklist_ambiguita if x.esito == "ambiguita_trovata"]
        escalate = [c for c in self.report if c.stato == "da_verificare"]
        if trovate and not escalate:
            raise ValueError("la checklist segnala ambiguità ma nessuna clausola del report "
                             "è da_verificare: incoerente")
        return self
