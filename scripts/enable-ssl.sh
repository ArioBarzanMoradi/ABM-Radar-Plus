#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo' >&2; exit 1; }
[[ $# -eq 1 || ($# -eq 3 && $2 == --webroot) ]] || { echo 'enable-ssl.sh DOMAIN [--webroot /existing/acme/webroot]' >&2; exit 2; }
domain=$1
[[ $domain =~ ^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$ && $domain != *..* ]] || exit 2
command -v certbot >/dev/null || { echo 'Install Certbot: sudo apt install certbot' >&2; exit 1; }
if [[ $# -eq 3 ]]; then
 [[ -d $3 ]] || { echo 'Webroot directory not found' >&2; exit 1; }
 certbot certonly --webroot -w "$3" -d "$domain"
else
 python3 - <<'PY'
import socket
with socket.socket() as s:
 try:s.bind(("0.0.0.0",80))
 except OSError:raise SystemExit("Port 80 is occupied. Use your existing ACME webroot or DNS validation; no service was stopped.")
PY
 certbot certonly --standalone -d "$domain"
fi
echo 'Certificate ready. Configure your domain and WebPath using configure-web.sh.'
echo 'Test renewal: sudo certbot renew --dry-run'
