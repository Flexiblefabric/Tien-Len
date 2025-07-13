#!/usr/bin/env bash
# Build a standalone Windows/Linux executable using PyInstaller.
# Requires the project dependencies and pyinstaller to be installed.

set -e

if [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "win32"* ]]; then
    SEP=';'
else
    SEP=':'
fi

pyinstaller --onefile --windowed --name tien-len \
  --add-data "assets${SEP}assets" tienlen_gui/view.py

