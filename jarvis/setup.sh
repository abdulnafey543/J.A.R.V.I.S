#!/usr/bin/env bash
# Thin wrapper kept for convenience: setup.py is the real installer.
cd "$(dirname "$0")" && exec python3 setup.py "$@"
