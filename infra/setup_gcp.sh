#!/bin/bash
# ============================================================================
# REGOLO — Setup del progetto GCP DEDICATO (decisione 2026-06-11:
# Cloud Run su progetto separato da quello di MAGI).
#
# Da eseguire UNA VOLTA, a mano (serve il login interattivo):
#   gcloud auth login            # se la CLI non è già autenticata
#   ./infra/setup_gcp.sh         # oppure: ./infra/setup_gcp.sh mio-project-id
#
# NOTA ISOLAMENTO: questo script NON tocca l'ADC condiviso della macchina
# (usato anche da MAGI): niente `set-quota-project`. Il codice REGOLO passa
# sempre il progetto esplicitamente (GOOGLE_CLOUD_PROJECT nel .env).
# ============================================================================
set -e

PROJECT_ID="${1:-regolo-loyalty-hma}"
REGION="europe-west1"

echo "▸ 1/4 — Creo il progetto $PROJECT_ID…"
gcloud projects create "$PROJECT_ID" --name="REGOLO Loyalty" \
  || echo "  (esiste già o ID occupato: in tal caso rilancia con un ID diverso)"

echo ""
echo "▸ 2/4 — Collega il BILLING (passaggio manuale, una volta sola):"
echo "  account disponibili:"
gcloud billing accounts list 2>/dev/null || gcloud beta billing accounts list 2>/dev/null || true
echo "  comando: gcloud billing projects link $PROJECT_ID --billing-account=XXXXXX-XXXXXX-XXXXXX"
read -r -p "  Premi INVIO quando il billing è collegato… "

echo "▸ 3/4 — Abilito le API (Vertex, Cloud Run, Secret Manager, Build)…"
gcloud services enable aiplatform.googleapis.com run.googleapis.com \
  secretmanager.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com --project "$PROJECT_ID"

echo "▸ 4/4 — Fatto. Ultimo passo manuale:"
echo "  aggiorna REGOLO/.env →  GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "                          GOOGLE_CLOUD_LOCATION=$REGION  (o us-central1 per i modelli)"
echo "  e verifica il compilatore: venv/bin/python mockup/01_contratto/compilatore.py"
echo ""
echo "✓ Setup completato. Il deploy Cloud Run (API + job) arriva con la Fase 1."
