# Veritas Infra V2.4.1 Release Manifest

## Release type
Post-consolidation hardening release for the unified institutional production repo.

## Included lines
- V2.3A core production spine
- V2.3B institutional intelligence
- V2.3C governance, regulatory, and country-scale layer

## V2.4.1 hardening changes
- fixed seed runtime defect in `backend/app/seed.py`
- aligned health endpoint version to `v2.4.1`
- stabilized backend tests by resetting in-memory rate-limit state between tests
- unified README for the consolidated repo
- cleaned packaging output

## Validation
- backend pytest suite: 14 passed
- Python compile validation: passed

## Notes
This release is the validated unified repo baseline for future development.
