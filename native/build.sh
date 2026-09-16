#!/usr/bin/env bash

# Refuse to rebuild under a running training. The linker rewrites the .so in
# place, and a process that has it mapped dies with SIGBUS: on 13 September a
# rebuild killed a raise-cap-2 solver 80 minutes into its run. FORCE=1 to
# override when that is what you want.
if [ -z "${FORCE:-}" ] && ps -eo args | grep -v grep | grep -qE "^(venv/bin/)?python[0-9.]* scripts/cfr/train_nolimit.py"; then
  echo "a training run is using the native module; finish it or FORCE=1" >&2
  exit 1
fi
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
