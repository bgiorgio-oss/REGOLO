"""
REGOLO — L2 MOTORE parametrico (Fase 1).

Esegue un Contratto di Gara su un feed di eventi-contratto e scrive gli eventi
di punti nel ledger (L3). È guidato SOLO dai parametri del contratto: nessuna
regola della gara è hardcoded qui. Zero LLM a runtime.

Gestisce le meccaniche reali incontrate sul pilota Enel B2B:
  - punti_per_unita   (bweb, rid: punti fissi per contratto)
  - punti_a_fasce     (power per kW, gas per classe: punti per scaglione)
  - storno            (cessazione: azzera i punti non utilizzati del partecipante)
  - riaccredito       (riattivazione: ripristina i punti azzerati)
  - bonus_condizionale, cap mensile, moltiplicatori temporali (dal mockup, generici)
e l'effective dating tra versioni di contratto.

Feed = lista di record cronologici, ognuno un dict:
  {tipo, partecipante, data:"YYYY-MM-DD", kpi, grandezza?, fascia?}
  tipo ∈ {attivazione, cessazione, riattivazione}

Determinismo: il feed viene ordinato per (data, partecipante, kpi, id);
nessun uso di now()/random; il replay con gli stessi input dà lo stesso ledger.
"""

from __future__ import annotations

from typing import Iterable

# ---------------------------------------------------------------------------
# Selezione contratto (effective dating) e meccaniche
# ---------------------------------------------------------------------------

def contratto_valido(contratti: list[dict], data: str) -> dict:
    """Il contratto della versione più alta valido alla data (YYYY-MM-DD)."""
    validi = [c for c in contratti
              if str(c["meta"]["valido_dal"])[:10] <= data <= str(c["meta"]["valido_al"])[:10]]
    if not validi:
        raise ValueError(f"nessun contratto valido alla data {data}")
    return max(validi, key=lambda c: c["meta"].get("contratto_versione", 1))


def trova_meccanica(contratto: dict, kpi: str) -> dict | None:
    """Match per id esatto, poi per contenimento del token kpi nell'id."""
    mecc = contratto["meccaniche"]
    for m in mecc:
        if m["id"] == kpi:
            return m
    for m in mecc:
        if kpi in m["id"]:
            return m
    return None


def _seleziona_fascia(meccanica: dict, grandezza=None, fascia=None) -> dict | None:
    """Trova lo scaglione: per range numerico (da<g<=a) o per etichetta."""
    fasce = meccanica.get("fasce") or []
    if fascia is not None:  # match esplicito per etichetta (es. classi gas)
        for f in fasce:
            if f.get("etichetta") == fascia:
                return f
        return None
    if grandezza is not None:  # match per range numerico
        for f in fasce:
            da, a = f.get("da"), f.get("a")
            if (da is None or grandezza > da) and (a is None or grandezza <= a):
                return f
    return None


def punti_per_attivazione(meccanica: dict, *, grandezza=None, fascia=None,
                          periodo=None) -> tuple[float, str]:
    """Ritorna (punti, dettaglio) per un contratto attivato. Solleva se la fascia
    non è determinabile (→ va in escalation, non si inventa un valore)."""
    tipo = meccanica["tipo"]
    if tipo == "punti_per_unita":
        punti = meccanica["punti"]
        for molt in meccanica.get("moltiplicatori") or []:
            if periodo in molt.get("periodi", []):
                punti *= molt["fattore"]
        return punti, f"{meccanica['id']}: {punti:g} pt"
    if tipo == "punti_a_fasce":
        f = _seleziona_fascia(meccanica, grandezza, fascia)
        if f is None:
            raise ValueError(f"fascia non determinabile per {meccanica['id']} "
                             f"(grandezza={grandezza}, fascia={fascia})")
        et = f.get("etichetta") or f"{f.get('da')}-{f.get('a')}"
        return f["punti"], f"{meccanica['id']} [{et}]: {f['punti']:g} pt"
    raise ValueError(f"tipo meccanica non gestito per attivazione: {tipo}")


# ---------------------------------------------------------------------------
# Esecuzione del feed sul ledger
# ---------------------------------------------------------------------------

def _meccanica_per_tipo(contratto: dict, tipo: str) -> dict | None:
    for m in contratto["meccaniche"]:
        if m["tipo"] == tipo:
            return m
    return None


def esegui(contratti: list[dict], feed: Iterable[dict], ledger, *, gara_id: str,
           run_id: str, stato: str = "contabilizzato") -> dict:
    """Processa il feed cronologico, scrive gli eventi nel ledger, ritorna un riepilogo.
    Mantiene i saldi correnti in memoria (servono a storni/riaccrediti = azzeramenti)."""
    records = sorted(feed, key=lambda r: (r["data"], r["partecipante"],
                                          r.get("kpi", ""), r.get("_i", 0)))
    saldo_corrente: dict[str, float] = {}      # punti maturati e non ancora persi
    azzerato_per: dict[str, float] = {}         # ultimo importo azzerato (per riaccredito)
    contatori = dict(attivazione=0, cessazione=0, riattivazione=0, ignorati=0, escalation=[])

    def emetti(part, tipo_ev, punti, mecc, periodo, descr, fonte, data):
        ledger.append(gara_id, part, tipo_ev, punti, payload={"feed_data": data},
                      meccanica=mecc, contratto_v=cv, periodo=periodo, run_id=run_id,
                      stato=stato, descrizione=descr, fonte_clausola=fonte,
                      creato_il=f"{data}T00:00:00")
        saldo_corrente[part] = saldo_corrente.get(part, 0) + punti

    for r in records:
        part, data, tipo = r["partecipante"], r["data"], r["tipo"]
        contratto = contratto_valido(contratti, data)
        cv = contratto["meta"].get("contratto_versione", 1)
        periodo = data[:7]

        if tipo == "attivazione":
            m = trova_meccanica(contratto, r["kpi"])
            if m is None:
                contatori["ignorati"] += 1; continue
            try:
                punti, descr = punti_per_attivazione(
                    m, grandezza=r.get("grandezza"), fascia=r.get("fascia"), periodo=periodo)
            except ValueError as e:
                contatori["ignorati"] += 1
                contatori["escalation"].append(str(e)); continue
            emetti(part, "accredito", punti, m["id"], periodo, descr,
                   m.get("fonte_clausola"), data)
            contatori["attivazione"] += 1

        elif tipo == "cessazione":
            m = _meccanica_per_tipo(contratto, "storno")
            attuale = saldo_corrente.get(part, 0)
            if attuale > 0:
                emetti(part, "storno", -attuale, m["id"] if m else "storno", periodo,
                       f"Cessazione rapporto: azzeramento di {attuale:g} pt non utilizzati",
                       m.get("fonte_clausola") if m else None, data)
                azzerato_per[part] = attuale
            contatori["cessazione"] += 1

        elif tipo == "riattivazione":
            m = _meccanica_per_tipo(contratto, "riaccredito")
            da_ripristinare = azzerato_per.get(part, 0)
            if da_ripristinare > 0:
                emetti(part, "riaccredito", da_ripristinare,
                       m["id"] if m else "riaccredito", periodo,
                       f"Riattivazione su stesso canale/P.IVA: riaccredito di {da_ripristinare:g} pt",
                       m.get("fonte_clausola") if m else None, data)
                azzerato_per[part] = 0
            contatori["riattivazione"] += 1

    return dict(record_processati=len(records), **contatori)
