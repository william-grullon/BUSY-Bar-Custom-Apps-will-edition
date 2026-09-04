#!/bin/zsh

cd "$(dirname "$0")/.." || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed."
  echo "Download it from: https://www.python.org/downloads/"
  echo
  read "reply?Press Return to close."
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Scene Generator requires Python 3.10 or newer."
  echo "Download it from: https://www.python.org/downloads/"
  echo
  read "reply?Press Return to close."
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  echo "Preparing Scene Generator for first use…"
  python3 -m venv .venv || exit 1
fi

source .venv/bin/activate
python -m pip install --quiet --disable-pip-version-check -r requirements.txt || exit 1

echo
python generate_scenes.py --interactive
status=$?

echo
if [[ $status -ne 0 ]]; then
  echo "Scene Generator stopped with an error. Check the message above."
fi
read "reply?Press Return to close."
exit $status
