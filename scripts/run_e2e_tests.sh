#!/bin/bash
source venv/bin/activate
export OLLAMA_URL="http://localhost:11434"
export MODEL="gemma4:e4b"

FILES=(
  "samples/01_requirements.md"
  "samples/API一覧.xlsx"
  "samples/FreeBSD AI Hack Report (Japanese).pptx"
  "samples/japanese-ja.docx"
  "samples/sample.txt"
)

echo "Starting End-to-End Sequential Test"
date

for f in "${FILES[@]}"; do
  echo ""
  echo "=========================================================="
  echo "Translating: ${f}"
  echo "=========================================================="
  python scripts/translate_cli.py -f "$f"
done

echo ""
echo "All tests finished!"
date
