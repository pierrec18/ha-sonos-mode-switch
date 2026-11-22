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

The repository is initially private. HACS's action explicitly refuses private
repositories, and the GitHub account connected to the target Marketplace cannot
read private repositories. Publication of this integration alone requires the
owner's approval; the service repository stays private.

Installed-file discovery, production token authentication, live entity availability
and rendered UI are not yet verified. No live topology transition has been triggered
by this integration during development.
