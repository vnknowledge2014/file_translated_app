#!/bin/bash
# Setup Ollama model for air-gapped deployment.
# Run this on an internet-connected machine, then transfer to air-gapped server.

set -e

echo "=== JP→VI Translation — Model Setup ==="
echo ""

# Check Ollama is running
if ! ollama list > /dev/null 2>&1; then
    echo "ERROR: Ollama is not running. Start it first: ollama serve"
    exit 1
fi

echo "[1/2] Pulling gemma4:e4b (Translation model, ~9.6GB)..."
ollama pull gemma4:e4b

echo ""
echo "[2/2] Verifying model..."
ollama list | grep -E "gemma4"

echo ""
echo "✅ Model ready! Transfer ~/.ollama/models to the air-gapped server."
echo "   Then run: docker compose up -d"
