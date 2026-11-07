# Verification — Jamshid Plus 1.1.0

Date: 2026-11-07
Environment: Linux x86_64, Python 3.12.14; headless Chromium.

## Completed

- TypeScript: npm run typecheck passed.
- Production frontend: npm run build passed.
- Python integration suite: 4 tests passed (unittest, isolated local processes).
- Shell syntax: bash -n passed for both installers and radarctl.
- UI flow: signed in, confirmed empty startup and missing metrics, switched and
  persisted appearance, created a host with its own address, issued its token,
  ran the actual Linux collector, received CPU/RAM and the live listening port,
  queued a TCP diagnostic from the UI, received its successful agent result,
  edited the host, deleted it and verified token rejection.
- Desktop dark/ivory and 390px mobile layouts inspected. No JavaScript errors.
- Project page anchors, mobile width and Pages repository links under a repository
  subpath verified locally. No GitHub repository or Pages publication was made.
- Included screenshots show the empty workspace; no credentials or fleet samples.

## Deployment scope

Systemd installation, a user's VPS, cross-country routing and ARM64 hardware
were not executed in this verification environment. The shipped wheel is pure
Python; there are no architecture-specific application binaries in the package.

## Reproduce

    npm ci
    npm run typecheck
    npm run build
    python3 -m unittest discover -s tests -v
    bash -n install.sh install-agent.sh scripts/radarctl
    python3 scripts/package.py
