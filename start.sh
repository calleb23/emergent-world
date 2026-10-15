#!/bin/sh
# Emergent World: get the latest code from GitHub, then watch it live in your browser.
# Keeps checking GitHub and restarts on new code by itself.
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check numpy
flags=""
while true; do
  git pull --ff-only --quiet
  python3 -m emergent_world.live --auto-update 2 $flags
  [ $? -eq 3 ] || break
  flags="--no-browser"
done
