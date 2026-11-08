# ABM Radar Plus 2.0

Self-hosted Persian Linux observability with independent panels, per-host agents and a peer monitoring network. Charcoal/ivory glass UI, local Vazirmatn, ARM64 and x86-64. Runtime: Python 3.10+, systemd; prebuilt web assets are committed. No Node.js or Docker is needed on a server.

Features: CPU, RAM, root disk, uptime/load/hostname/kernel; per-interface counters and rates; IPv4/IPv6 addresses/routes and DNS; TCP/UDP listeners and binds; VPN unit/interface discovery; up to 24 custom TCP/ICMP targets; opt-in IPv4, IPv6, DNS, HTTPS, ICMP and STUN checks; queued Ping/TCP/UDP/DNS/trace/HTTPS/TLS/IPv4/IPv6/STUN diagnostics; SQLite history, alerts, notes, checklists; username/password/session CLI; HTTPS/WebPath helpers.

Peer panels export only locally owned observations. They never recursively re-export other panels, credentials or private notes. Each panel continues local monitoring during a partition and marks cached peer readings stale. A peer key is read-only unless its issuer explicitly grants diagnostic permission. Keys for agents and panels are separate. Add every other panel on each panel for a complete network view.

```bash
sudo apt install git python3 iproute2 iputils-ping traceroute
git clone https://github.com/ArioBarzanMoradi/ABM-Radar-Plus.git
cd ABM-Radar-Plus
sudo bash install.sh
```

Create a host record, issue its agent key and run `sudo bash install-agent.sh` on that host. When panel and agent share a host, use `http://127.0.0.1:8788` and that panel's key. See [HTTPS/WebPath setup](guides/webpath-fa.md). Port 443 is left available for existing VPN services.

First upgrade from an earlier Plus checkout: `git pull --ff-only`, then `sudo bash update.sh --source "$PWD"`. Subsequent upgrades: `sudo abm-radarctl update`. Online SQLite/config backups precede upgrades. Failed panel restarts/HTTP health checks roll code and service configuration back; additive schema migrations remain. Agent restart failures restore prior agent files and clearly report a partial upgrade. Existing accounts, keys, ping target, public URL, port, WebPath and Nginx configuration are preserved. Legacy data/service names and CLI aliases remain for compatibility; they are not duplicate installations. An independent older `network-radar` installation is not automatically migrated.

Local socket listening, ICMP success, STUN response and active VPN units each describe a limited observation, not proof of all inbound reachability or a working VPN. Empty measurements remain empty. Systemd and external Internet paths still need verification on the deployment hosts; see [verification](VERIFICATION.md).

Development: `npm ci`, `npm run typecheck`, `npm run build`, `python3 -m unittest discover -s tests -v`. Package: `python3 scripts/package.py`. GitHub Pages serves `docs/` as a project website, never live private monitoring. MIT license; bundled dependency licenses in `licenses/`.
