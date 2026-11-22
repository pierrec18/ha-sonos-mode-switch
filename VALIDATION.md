# Validation — 0.1.0

## Simulated validation

- Target: Home Assistant Core 2026.11.2, Python 3.14.
- 23 tests: setup/unload/reload; user and duplicate flows; options reload;
  token reauthentication; authentication errors; offline recovery; accepted versus
  observed mode; concurrent-operation guards; read-only and stale/reachability guards;
  HTTP redirect/error rejection; ambiguous submit timeout without automatic retry.
- Coverage: 95% of integration statements on the local validation run.
- Ruff lint and formatting; compileall; archive layout verified.
- Network sockets disabled in tests; no production credentials or speaker mutations.
- HA Core's hassfest validation passed on GitHub Actions.

## Deployment gates

The owner authorized publication of this integration-only repository on 2026-11-22.
The Sonos service repository remains private. No production credentials are included.

The 0.1.0 files were installed manually and discovered by Core after restart.
Production authentication and live entities remain blocked by API network reachability.
Rendered UI and live topology transitions have not been verified.
