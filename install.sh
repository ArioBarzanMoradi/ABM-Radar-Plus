#!/usr/bin/env bash
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$src/jamshid-plus/install.sh" "$@"
