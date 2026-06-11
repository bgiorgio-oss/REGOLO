# Spike ZEN Engine — RISULTATO (2026-06-11)

**Domanda**: il Contratto di Gara può essere transpilato in JDM ed eseguito da
[GoRules ZEN Engine](https://github.com/gorules/zen) ottenendo gli stessi numeri del
nostro motore?

**Risposta: SÌ — equivalenza perfetta.**

```
Valutazioni ZEN: 74 (PV × mese) in 39 ms (0.53 ms/valutazione)
Celle confrontate (pv, periodo, meccanica): 392
✓ ZERO DIVERGENZE: ZEN riproduce il motore al 100%
```

## Cosa è stato verificato

- `pip install zen-engine` funziona su macOS Intel x86_64 / Python 3.12 (wheel nativa, in-process)
- Il transpiler (`spike_zen.py`) genera i JDM **leggendo i parametri dal contratto** (punti,
  cap, moltiplicatori, soglie bonus): il contratto resta la fonte, il JDM è l'eseguibile
- Tutte le meccaniche SAM2026 sono esprimibili nello Zen Expression Language:
  cap → `min([...])`, moltiplicatore stagionale → `periodo in [...] ? f : 1`,
  bonus condizionali → ternari con `and`, storni negativi
- **Effective dating fuori da ZEN, nel nostro layer** (come da design): v1 per aprile/maggio,
  v2 da giugno — selezione del file JDM per periodo
- Determinismo preservato: nessun `now()` nelle espressioni, la data è solo input

## Decisione conseguente

In **Fase 1** il motore L2 = **ZEN Engine + nostro layer** (effective dating, replay,
quarantena, ledger, orchestrazione). Il motore Python del mockup resta come riferimento
e doppio controllo (golden test incrociato: due implementazioni indipendenti che devono
coincidere — pattern riconciliazione interno).

## Limiti dello spike

- Coperte le meccaniche di SAM2026 (punti/unità, cap, moltiplicatori, bonus condizionali,
  storni). Meccaniche più complesse (instant win, fasce progressive, classifiche dentro
  l'engine) andranno provate sui regolamenti reali — JDM ha anche decision table e switch
  node non ancora usati qui.
- Classifiche e aggregazioni multi-PV restano fuori da ZEN (sono sul nostro layer, corretto così).

File: `spike_zen.py` (transpiler + runner), `zen_sam2026_v1.json` / `v2.json` (JDM generati).
