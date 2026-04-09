# Repository Instructions for GitHub Copilot

## Project Overview

**Tweaks** is a reusable infrastructure Frappe/ERPNext app that adds advanced framework capabilities used across the Grupo Soldamundo stack:

- **Access Control (AC) Rules** — rule-based, principal/resource permission system layered on top of standard Frappe roles
- **Async Tasks** — priority-ordered background job framework with concurrency limits, auto-retry, and cancellation (`async_task_log`, `async_task_type`)
- **Sync Jobs** — structured SAP↔Frappe data synchronisation framework (consumed heavily by the `soldamundo` app)
- **Document Review** — configurable multi-step review/approval workflow system
- **Business Logic** — scriptable, categorised server-side logic modules with category linking
- **Observability** — OpenObserve API integration for logging, metrics, and audit trails
- **Typst** — PDF/PNG/SVG document generation from Typst markup
- **Power Query** — long-polling report bridge for Power BI / Excel data integration
- **Google** — Google Service Account + Spreadsheet integration
- **Peru/SUNAT** — Peruvian identity document types and API utilities (`peru_api_com`)

Key Python utilities live in `tweaks/utils/`: `access_control.py`, `async_task.py`, `sync_job.py`, `document_review.py`, `typst.py`, `report_long_polling.py`, `workflow.py`.

## ⚠️ Always Check Skills First

Before working on any feature, load the relevant skill:

| Area | Skill |
|---|---|
| AC Rules / permissions | `frappe-tweaks-ac-rules-expert` |
| Async Tasks | `frappe-tweaks-async-tasks` |
| Document Review | `frappe-tweaks-document-review-expert` |
| OpenObserve API | `frappe-tweaks-open-observe-api-expert` |
| Power Query / Power BI | `frappe-tweaks-power-query-expert` |
| Sync Jobs | `frappe-tweaks-sync-job-expert` |
| Typst PDF generation | `frappe-typst-expert` |

Skills are in `.agents/skills/`.

## Build & Test

```bash
bench migrate
bench run-tests --app tweaks
# Omit --site; default site development.localhost is used automatically
```

## Code Quality

```bash
cd apps/tweaks
pre-commit run --all-files
```
