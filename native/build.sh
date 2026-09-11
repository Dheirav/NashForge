#!/usr/bin/env bash
# Build the native module into native/build and copy it beside the Python.
#
# The interpreter is passed explicitly: this repo has a venv, and CMake's own
# search will happily find the system Python and build a module that imports and
# then crashes on a subtly different ABI.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
python="${here}/../venv/bin/python"
cmake -S "$here" -B "$here/build" -G Ninja \
      -DPython_EXECUTABLE="$python" -DCMAKE_BUILD_TYPE=Release "$@" >/dev/null
cmake --build "$here/build" --parallel
cp "$here"/build/pokerbot_native*.so "$here/../"
echo "built $(ls "$here"/build/pokerbot_native*.so)"
