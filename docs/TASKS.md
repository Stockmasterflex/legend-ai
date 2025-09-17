# Task Tracker

## Phase 4 – Reliability & Ops
- [x] Tighten CI pipeline (ruff/black/pytest, npm lint/build). _CI now fails on lint/test regressions and runs Next lint/build._
- [x] Document scan filters + chart metadata (docs/SCANNER.md). _Docs cover timeframe filters, liquidity options, and the new chart meta contract._
- [x] Add structured request metrics for chart proxy. _Prometheus counters/histograms now track fallback status and render latency._
- [x] Extend `legend_check.sh` to validate timeframe and overlay endpoints. _Smoke script hits weekly scans and POST /chart with overlays._

## Phase 5 – Deploy & Verify
- [x] Deploy API + frontend + shots via Makefile scripts. _Render + Vercel redeploys triggered via `make deploy` / `make deploy-shots`._
- [ ] Run `make check`, `make top5`, and capture frontend scan results post-deploy.

## Phase 6 – Stretch Goals
- [ ] Investigate pagination / streaming results for `/api/v1/scan`.
