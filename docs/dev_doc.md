# Developer Documentation

## Next Features (Planned)
- Bulk CSV export
- API endpoints for integrations

## Routing & Template Contracts
- Pénzügy always resolves to `/dashboard/penzugy`.
- Accountant dashboard and list pages share a query helper for consistent ordering and filtering.
- Macros treat `query_params` and `users_map` as optional (safe defaults).

## Maintenance Notes
- If a role dashboard renders a macro expecting `query_params`, always pass `request.args.to_dict()`; macros are safe but views should remain explicit.

## Change Log
- 2025-08-22 – Removed "Auto-close overdue cases" from plan; documented routing & template contracts.
- 2025-08-25 – Normalize final status to `lezárt`; add locked-case guards, workflow checks, idempotent tox doc, and tests.
- 2025-09-01 – Idempotency: Added `IdempotencyToken` table + helpers; applied to certificate, tox doc, signaling assignments, describer assign, and case creation (TTL 5m, configurable). Stale-Form Protection: hidden `form_version` on edit/assign forms with server rejection of outdated submissions. Tests cover duplicate-submit suppression and stale-form rejections.
## Changelog / UI Terminology
- [2025-08-25] Renamed:
  - Sidebar: “Összes ügy” → “Összes boncolás”
  - Cases list heading: “Nyitott ügyek” → “Boncolási ügyek folyamatban”
  Notes: Left dashboard phrases as-is; added TODO comments to review for consistency later.