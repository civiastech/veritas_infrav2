# Original Prototype Alignment Matrix

## Alignment principle

This merged build aligns the strongest real deployment repo with the original prototype's doctrine and module surface.

## Prototype coverage carried into this build

### Directly represented in backend routes
- IDENT / professionals
- TWIN / projects + twin events
- BUILD / evidence
- VISION / inspections
- PAY / milestones + payments
- SEAL / certifications
- MARKET / tenders
- ORIGIN / materials
- MONITOR / sensors + alerts
- LEX / disputes
- ATLAS / portfolio + reports
- VERIFUND / products + applications
- ACADEMY / paths + courses + credentials
- CLONE / rollout summary
- Governance
- Regulatory
- Workflow engine
- Policy engine
- Platform / country configuration
- Audit trail
- Notifications

### Directly represented in canonical frontend experience
- the full original institutional visual system
- role switching
- dashboard posture
- platform modules and doctrine language
- Lighthouse projects framing
- professional registry concepts
- SHI / PRI / evidence-first narrative
- escrow and certification framing
- materials verification / disputes / sensors / notifications

## Remaining gap

The prototype frontend is still richer than the current backend-linked operational console in terms of institutional storytelling, ceremonial UX, and some deep interactive mock flows. Those are preserved visually and functionally in the prototype frontend, but not every one of those flows is yet reimplemented as API-backed production screens.

## Recommended path after this baseline
1. progressively bind prototype screens to live `/api/v1` endpoints
2. unify auth/session across prototype and ops console
3. replace in-browser mock persistence in prototype flows with real backend services
4. add country-tenant and regulator-specific dashboards on top of workflow/policy/platform configuration
