#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then
  echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again."
  read -r -p "Press Enter to close" _; exit 1
fi
[ -x .venv/bin/python ] || "$PY" -m venv .venv || { echo "Could not create the environment."; read -r -p "Press Enter" _; exit 1; }
if [ ! -f .venv/.installed ]; then
  echo "Installing libraries (first time only, internet required)..."
  .venv/bin/python -m pip install --upgrade pip && .venv/bin/python -m pip install -r requirements.txt \
    && touch .venv/.installed || { echo "Installation failed. Check the internet and try again."; read -r -p "Press Enter" _; exit 1; }
fi
mkdir -p "$HOME/.streamlit"
[ -f "$HOME/.streamlit/credentials.toml" ] || printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"
echo "Starting AI Study Buddy. Keep this window open while using the app."
exec .venv/bin/python -m streamlit run app.py
