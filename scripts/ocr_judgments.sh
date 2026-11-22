#!/bin/sh
# OCR the scanned judgments (English), then run the military filter on them and checkpoint.
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
$PY -W ignore -m pipeline ocr --langs eng --workers 4 > state/logs/ocr_judgments.log 2>&1
$PY -W ignore -m pipeline all > state/logs/ocr_after.log 2>&1
$PY scripts/push_data.py "after OCR of scanned judgments" >> state/logs/ocr_after.log 2>&1
$PY scripts/push_hf.py "after OCR of scanned judgments" >> state/logs/ocr_after.log 2>&1
