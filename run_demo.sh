#!/bin/bash
# REGOLO — avvio demo end-to-end
# Uso: ./run_demo.sh [--reset]   (--reset rigenera anche i dati mock)
set -e
cd "$(dirname "$0")"

# 1. venv locale (separato da qualsiasi altro progetto)
if [ ! -d venv ]; then
  echo "▸ Creo il venv locale…"
  python3 -m venv venv
fi
venv/bin/pip install -q -r requirements.txt

# 2. dati mock (solo se mancanti o con --reset)
if [ "$1" = "--reset" ] || [ ! -f mockup/02_dati/anagrafica.csv ]; then
  echo "▸ Genero i dati mock…"
  venv/bin/python mockup/02_dati/genera_dati.py
fi

# 3. motore deterministico → ledger + state
echo "▸ Eseguo il motore…"
venv/bin/python mockup/03_motore/motore.py

# 4. API + frontend
echo ""
echo "════════════════════════════════════════════════════"
echo "  REGOLO demo attiva"
echo "  Frontend utente : http://localhost:8788/"
echo "  Backoffice      : http://localhost:8788/backoffice"
echo "  API             : http://localhost:8788/api/gara"
echo "════════════════════════════════════════════════════"
echo ""
exec venv/bin/python mockup/04_api/api.py
