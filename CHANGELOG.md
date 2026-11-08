# Changelog

## 2.0.0 — 2026-11-08

- Rename product, frontend, login, CLI, package, website and documentation to ABM Radar Plus.
- Restore previous Radar observability: disk/uptime/load/hostname/kernel, per-interface traffic, IPv4/IPv6 routes/addresses and DNS, bound TCP/UDP listeners and known VPN units/interfaces.
- Add opt-in bounded protocol checks and up to 24 independent outbound TCP/ICMP targets per agent; extend manual diagnostics with HTTPS, TLS/SNI, IPv4, IPv6 and transaction-verified STUN.
- Add peer panels: local-only exports, independent local databases, node identity pinning, bounded polling, stale cached readings, read-only keys and explicit remote diagnostic scope. No recursive replication.
- Add disk and traffic history, disk threshold alerts and responsive health/network pages; keep existing checklists, notes, events and agent job leases.
- Add `abm-radarctl update`, pre-upgrade online SQLite/config backups, health-checked panel rollback and agent rollback on restart failure. Preserve existing accounts, keys, services, public port and WebPath.
- Move the maintained application to repository root; remove duplicated obsolete trees from the working tree. Git history preserves prior versions.
- Add multi-panel HTTP, observability, authentication and isolated installer upgrade/rollback checks.

## Previous Plus versions

1.2 added prefix-aware panel/agent URLs and Nginx configuration. 1.1 introduced native Linux deployment, real outbound agents, empty inventory and persistent monitoring. Those installed Plus layouts remain upgrade-compatible.
