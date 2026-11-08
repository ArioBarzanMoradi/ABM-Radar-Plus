#!/usr/bin/env bash
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ $# -eq 0 || ($# -eq 1 && $1 == --configure) ]] || { echo 'sudo bash install-agent.sh [--configure]' >&2; exit 2; }
[[ $EUID == 0 && -d /run/systemd/system ]] || { echo 'با sudo روی یک میزبان لینوکسی با systemd اجرا کنید.' >&2; exit 1; }
/usr/bin/python3 -c 'import sys; assert sys.version_info >= (3,10)'
getent passwd radar-agent >/dev/null || useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin radar-agent
install -d -m 0755 /opt/radar-agent
install -d -m 0750 -o root -g radar-agent /etc/radar-agent
cfg=/etc/radar-agent/config.json
if [[ ! -f $cfg || "${1:-}" == --configure ]]; then
 /usr/bin/python3 "$src/agent/agent.py" --config "$cfg" --configure
fi
chown root:radar-agent "$cfg"; chmod 0640 "$cfg"
temp=$(mktemp -d)
trap 'rm -rf -- "$temp"' EXIT
for part in agent.py system_metrics.py network_checks.py; do
 if [[ -f /opt/radar-agent/$part ]]; then cp -p "/opt/radar-agent/$part" "$temp/$part"; fi
 install -m 0644 "$src/agent/$part" "/opt/radar-agent/$part.new"
done
if [[ -f /etc/systemd/system/radar-agent.service ]]; then cp -p /etc/systemd/system/radar-agent.service "$temp/unit"; fi
# A running process keeps its imported modules; stage all files before restarting it.
for part in system_metrics.py network_checks.py agent.py; do mv -f "/opt/radar-agent/$part.new" "/opt/radar-agent/$part"; done
install -m 0644 "$src/deploy/radar-agent.service" /etc/systemd/system/radar-agent.service
systemctl daemon-reload
if ! systemctl restart radar-agent.service || ! systemctl is-active --quiet radar-agent.service; then
 if [[ -f "$temp/agent.py" && -f "$temp/unit" ]]; then
  for part in agent.py system_metrics.py network_checks.py; do
   if [[ -f $temp/$part ]]; then install -m 0644 "$temp/$part" "/opt/radar-agent/$part"; fi
  done
  install -m 0644 "$temp/unit" /etc/systemd/system/radar-agent.service
  systemctl daemon-reload; systemctl restart radar-agent.service || true
 fi
 echo 'ارتقای عامل کامل نشد؛ نسخهٔ قبلی در صورت وجود بازگردانده شد.' >&2; exit 1
fi
systemctl enable radar-agent.service >/dev/null
ln -sfn /etc/systemd/system/radar-agent.service /etc/systemd/system/abm-radar-agent.service
systemctl daemon-reload
printf 'عامل راه‌اندازی شد. در صفحهٔ جزئیات سرور، زمان آخرین نمونه را بررسی کنید.\n'
