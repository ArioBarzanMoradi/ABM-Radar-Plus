#!/usr/bin/env bash
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$src/jamshid-plus/scripts/configure-web.py" "$@"
