# Verification — ABM Radar Plus 2.0.0

Verified locally on 2026-11-08:

- TypeScript strict typecheck and production esbuild build.
- 19 Python tests pass: real HTTP panels and outbound agent processes, account/session/CSRF checks, empty inventory, one-time agent keys and revocation, real TCP success/failure, inconclusive silent UDP, job isolation/idempotency and persistent data.
- Multi-panel tests cover local-only exports, distinct peer/agent keys, read versus test scope, remote jobs executed by the source agent, cached partitions with independent local writes, pinned node identity, self-peer rejection, redacted keys, invalid replies and key rotation.
- Observability tests cover real Linux disk/uptime/network counters and listening sockets; missing tools; bounded probes; TCP versus ICMP separation; transaction-matching STUN; local HTTPS with trusted versus untrusted certificates and TLS expiry; monitoring configuration delivery and extended history.
- Migration tests reopen the prior Plus schema without the three new tables and preserve accounts, agent keys and notes. Legacy agent payloads remain accepted.
- Installer tests execute the shell updater and installers against a translated temporary filesystem with mocked ownership and service-management commands. Actual Python HTTP health, SQLite backup, source copies and atomic symlink selection are exercised. They verify preserved settings/credentials, panel rollback after a failed restart and agent rollback with explicit partial-upgrade reporting.
- Shell syntax and Python compilation checks pass.

The installer harness does not emulate systemd hardening, real service users, Nginx, ACME challenges, provider firewalls or Iran–abroad paths. No SSH access to deployment hosts was used. CPU/traffic/routing visibility depends on host permissions and tools. Validate status and connectivity on each deployment host after upgrading.

The public screenshots show a fresh empty installation with ABM Radar Plus branding. No operational server inventory, credentials or private panel URLs are included.
