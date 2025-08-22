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