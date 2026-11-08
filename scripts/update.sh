#!/usr/bin/env bash
# Update only from this project's repository; the installer checks health and rolls back code on failure.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run: sudo abm-radarctl update' >&2; exit 1; }
ref=main
source_dir=""
while (($#)); do
 case "$1" in
  --ref) [[ $# -ge 2 ]] || exit 2; ref=$2; shift 2;;
  --source) [[ $# -ge 2 ]] || exit 2; source_dir=$2; shift 2;;
  *) echo 'abm-radarctl update [--ref main|TAG] [--source /trusted/checkout]' >&2; exit 2;;
 esac
done
[[ $ref =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ && $ref != *..* ]] || { echo 'Invalid ref' >&2; exit 2; }
umask 077
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
backup=/var/backups/abm-radar-plus/$(date -u +%Y%m%dT%H%M%S)-$$
install -d -m 0700 "$backup"
if [[ -f /opt/radar-infra/current/run.py ]]; then
 install -d -m 0700 -o radar-panel -g radar-panel /var/lib/radar-infra/backups
 db_backup=/var/lib/radar-infra/backups/pre-update-$(date -u +%Y%m%dT%H%M%S)-$$.sqlite3
 runuser -u radar-panel -- /usr/bin/python3 /opt/radar-infra/current/run.py --data-dir /var/lib/radar-infra backup "$db_backup"
 cp -p "$db_backup" "$backup/database.sqlite3"
fi
for directory in /etc/radar-infra /etc/radar-agent; do
 if [[ -d $directory ]]; then cp -a "$directory" "$backup/"; fi
done
echo "Backup: $backup"
if [[ -z $source_dir ]]; then
 command -v git >/dev/null || { echo 'Install git first: sudo apt install git' >&2; exit 1; }
 if ! git clone --quiet --depth 1 --branch "$ref" -- https://github.com/ArioBarzanMoradi/ABM-Radar-Plus.git "$work/source"; then
  # GitHub redirects old clones after a repository rename. This fallback also permits staged rename rollout.
  rm -rf -- "$work/source"
  git clone --quiet --depth 1 --branch "$ref" -- https://github.com/ArioBarzanMoradi/Jamshid-Radar-Plus.git "$work/source"
 fi
 source_dir=$work/source
fi
source_dir=$(cd -- "$source_dir" && pwd)
if [[ -f $source_dir/abm-radar-plus/run.py ]]; then source_dir=$source_dir/abm-radar-plus;
elif [[ -f $source_dir/jamshid-plus/run.py ]]; then source_dir=$source_dir/jamshid-plus; fi
[[ -f $source_dir/VERSION && -f $source_dir/install.sh && -f $source_dir/run.py ]] || { echo 'Invalid ABM Radar Plus source' >&2; exit 1; }
# Syntax-check in the private update directory, never write caches into the checkout.
python3 - "$source_dir" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
for sub in ("radar","agent"):
 for p in (root/sub).glob("*.py"):compile(p.read_text(),str(p),"exec")
compile((root/"run.py").read_text(),str(root/"run.py"),"exec")
PY
(cd "$source_dir" && sha256sum --check vendor/SHA256SUMS)
if ! bash "$source_dir/install.sh"; then
 echo "Panel update failed. Backup: $backup. See installer output; a failed service restart or HTTP health check restores the previous code." >&2; exit 1
fi
if [[ -f /etc/radar-agent/config.json ]] && ! bash "$source_dir/install-agent.sh"; then
 echo "Panel updated; agent update failed. Check: sudo abm-radarctl status. Backup: $backup" >&2; exit 1
fi
printf 'ABM Radar Plus %s updated. Settings, URL, accounts and agent keys were preserved.\n' "$(cat "$source_dir/VERSION")"
