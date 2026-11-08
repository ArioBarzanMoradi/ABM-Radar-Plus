#!/usr/bin/env bash
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
requested=""
case "$#" in
 0) ;;
 2) [[ $1 == --port && $2 =~ ^[1-9][0-9]{3,4}$ ]] || { echo 'sudo bash install.sh [--port 8788]' >&2; exit 2; }; requested=$2 ;;
 *) echo 'sudo bash install.sh [--port 8788]' >&2; exit 2 ;;
esac
[[ $EUID == 0 ]] || { echo 'sudo bash install.sh' >&2; exit 1; }
[[ -d /run/systemd/system ]] || { echo 'این نصب‌کننده به لینوکس با systemd فعال نیاز دارد.' >&2; exit 1; }
/usr/bin/python3 -c 'import sys, sqlite3, hashlib; assert sys.version_info >= (3,10) and hasattr(hashlib,"scrypt")'
for part in run.py radar/web.py docs/assets/app.js docs/assets/style.css vendor/waitress-3.0.2-py3-none-any.whl; do
  [[ -s "$src/$part" ]] || { echo "فایل بسته پیدا نشد: $part" >&2; exit 1; }
done
dest=/opt/radar-infra
conf=/etc/radar-infra/panel.env
oldport=""
if [[ -f $conf ]]; then oldport=$(sed -n 's/^RADAR_PORT=//p' "$conf" | head -1); fi
port=${requested:-${oldport:-8788}}
[[ $port =~ ^[1-9][0-9]{3,4}$ ]] && (( port >= 1024 && port <= 65535 )) || { echo 'یک پورت بین ۱۰۲۴ و ۶۵۵۳۵ وارد کنید.' >&2; exit 1; }
if [[ $port != "$oldport" ]] || ! systemctl is-active --quiet radar-infra.service; then
 /usr/bin/python3 - "$port" <<'PY'
import sys,socket
with socket.socket() as s:
    try: s.bind(("127.0.0.1",int(sys.argv[1])))
    except OSError: sys.exit("پورت در حال استفاده است. مثلاً sudo bash install.sh --port 8788 را اجرا کنید.")
PY
fi
getent passwd radar-panel >/dev/null || useradd --system --user-group --no-create-home --home-dir /var/lib/radar-infra --shell /usr/sbin/nologin radar-panel
install -d -m 0755 "$dest/releases" /etc/radar-infra
install -d -m 0700 -o radar-panel -g radar-panel /var/lib/radar-infra
release=$(mktemp -d "$dest/releases/radar.XXXXXXXX")
chmod 0755 "$release"
install -d -m 0755 "$release"/{radar,deploy,docs,vendor}
install -m 0644 "$src/run.py" "$release/run.py"
install -m 0644 "$src/VERSION" "$release/VERSION"
if [[ -f "$src/.source-commit" ]]; then install -m 0644 "$src/.source-commit" "$release/.source-commit"; fi
install -m 0644 "$src"/radar/*.py "$release/radar/"
install -m 0644 "$src"/vendor/*.whl "$release/vendor/"
install -m 0644 "$src"/deploy/{login,panel}.html "$release/deploy/"
install -m 0644 "$src"/docs/index.html "$release/docs/"
cp -R "$src/docs/assets" "$release/docs/"
chmod -R a+rX,go-w "$release"
# Back up the existing SQLite data before additive schema migration.
if [[ -f "$dest/current/run.py" ]]; then
 install -d -m 0700 -o radar-panel -g radar-panel /var/lib/radar-infra/backups
 runuser -u radar-panel -- /usr/bin/python3 "$dest/current/run.py" --data-dir /var/lib/radar-infra backup "/var/lib/radar-infra/backups/pre-install-$(date -u +%Y%m%dT%H%M%S)-$$.sqlite3"
fi
# Initialize credentials before switching the live service to this release.
runuser -u radar-panel -- /usr/bin/python3 "$release/run.py" --data-dir /var/lib/radar-infra init
old=$(readlink -f "$dest/current" || true)
temp=$(mktemp -d)
trap 'rm -rf -- "$temp"' EXIT
if [[ -f $conf ]]; then cp -p "$conf" "$temp/panel.env"; fi
if [[ -f /etc/systemd/system/radar-infra.service ]]; then cp -p /etc/systemd/system/radar-infra.service "$temp/unit"; fi
if [[ -f $conf ]]; then
  sed '/^RADAR_PORT=/d' "$conf" > "$temp/new.env"
else
  printf 'RADAR_PUBLIC_ORIGIN=\n' > "$temp/new.env"
fi
printf 'RADAR_PORT=%s\n' "$port" >> "$temp/new.env"
install -m 0644 "$temp/new.env" "$conf"
install -m 0644 "$src/deploy/radar-infra.service" /etc/systemd/system/radar-infra.service
switch_to() { ln -s "$1" "$dest/current.next.$$"; mv -Tf "$dest/current.next.$$" "$dest/current"; }
switch_to "$release"
systemctl daemon-reload
healthy() {
 /usr/bin/python3 - "$port" <<'PY'
import json,sys,time,urllib.request
url="http://127.0.0.1:"+sys.argv[1]+"/healthz"
for attempt in range(18):
    try:
        with urllib.request.urlopen(url,timeout=1) as r:
            if json.load(r).get("status")=="ok": sys.exit(0)
    except Exception: pass
    time.sleep(.4)
sys.exit(1)
PY
}
if ! systemctl restart radar-infra.service || ! healthy; then
  journalctl -u radar-infra.service --no-pager -n 15 >&2 || true
  if [[ -d "$old" && "$old" != "$dest/current" && -f "$temp/panel.env" && -f "$temp/unit" ]]; then
    switch_to "$old"; install -m 0644 "$temp/panel.env" "$conf"
    install -m 0644 "$temp/unit" /etc/systemd/system/radar-infra.service
    systemctl daemon-reload; systemctl restart radar-infra.service || true
  fi
  echo 'پایش سلامت پنل موفق نشد.' >&2; exit 1
fi
systemctl enable radar-infra.service >/dev/null
# Preserve old service/data identities so existing installations remain a single instance.
ln -sfn /etc/systemd/system/radar-infra.service /etc/systemd/system/abm-radar-plus.service
for pair in /opt/abm-radar-plus:/opt/radar-infra /etc/abm-radar-plus:/etc/radar-infra /var/lib/abm-radar-plus:/var/lib/radar-infra; do
 alias_path=${pair%%:*}; target_path=${pair#*:}
 if [[ ! -e $alias_path ]]; then ln -s "$target_path" "$alias_path"; fi
done
systemctl daemon-reload
install -d -m 0755 /usr/local/lib/abm-radar-plus /usr/local/bin
install -m 0755 "$src/scripts/update.sh" /usr/local/lib/abm-radar-plus/update.sh
install -m 0755 "$src/scripts/radarctl" /usr/local/bin/abm-radarctl
install -m 0755 "$src/scripts/radarctl" /usr/local/bin/radarctl
install -m 0755 "$src/scripts/radarctl" /usr/local/bin/jamshidctl
printf 'پنل آماده است: http://127.0.0.1:%s\n' "$port"
printf 'روی مک: ssh -NT -L 127.0.0.1:%s:127.0.0.1:%s USER@SERVER_IP\n' "$port" "$port"
