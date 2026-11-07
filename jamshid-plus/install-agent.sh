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
install -m 0644 "$src/agent/agent.py" /opt/radar-agent/agent.py.new
mv -f /opt/radar-agent/agent.py.new /opt/radar-agent/agent.py
install -m 0644 "$src/deploy/radar-agent.service" /etc/systemd/system/radar-agent.service
systemctl daemon-reload
systemctl enable radar-agent.service >/dev/null
systemctl restart radar-agent.service
printf 'عامل راه‌اندازی شد. در صفحهٔ جزئیات سرور، زمان آخرین نمونه را بررسی کنید.\n'
