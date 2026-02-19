# Skills Catalog

Summary of all available skills in this repository. Review before creating a new skill to avoid duplication.

## Frappe Tweaks – Domain Skills

### ac-rules-expert
**When to use:** Working with AC Rules, Query Filters, AC Resources, or AC Actions; implementing fine-grained record-level access control; debugging permission issues; integrating access control with DocTypes, Reports, or Workflows.  
**What it covers:** The Frappe Tweaks AC Rule system — rule evaluation, SQL generation, Permit/Forbid semantics, principal/resource filters, debugging reports (AC Permissions, Query Filters, AC Principal Query Filters), and troubleshooting.

### document-review-expert
**When to use:** Working with Document Review Rules or Document Reviews; implementing review/approval workflows; creating validation scripts; understanding review lifecycle or auto-assignment of reviewers.  
**What it covers:** The Frappe Tweaks Document Review system — rule scripts, review lifecycle (Draft/Submitted/Cancelled), automatic banner, timeline integration, workflow integration via `get_document_review_status()`, permission-aware display, and troubleshooting.

### open-observe-api-expert
**When to use:** Creating or configuring the OpenObserve API DocType; implementing `send_logs()` or `search_logs()`; integrating with Server Scripts or Business Logic; debugging connection issues; implementing logging, monitoring, error tracking, or audit trails.  
**What it covers:** OpenObserve API integration — configuration, `send_logs()`, `search_logs()`, dry run, safe_exec globals, timestamp handling, and troubleshooting.

### power-query-expert
**When to use:** Connecting Power BI or Excel (Power Query) to Frappe; building M code for Frappe data access; handling long-running reports to avoid timeouts; configuring authentication.  
**What it covers:** Power Query M code patterns — REST API, direct report API, `report_long_polling` API for heavy reports, authentication (username/password and API key/token), column type transformations, and cache-busting.

### sync-job-expert
**When to use:** Creating, implementing, or troubleshooting Sync Jobs; working with Sync Job Types or controllers; enqueueing sync jobs; understanding sync job lifecycle.  
**What it covers:** Frappe Tweaks Sync Job framework — Sync Job Types, controllers (Standard/Bypass modes), enqueueing, status flow, dry run, troubleshooting.

---

## Frappe Framework – Core Skills

### doctype-schema-expert
**When to use:** Creating or modifying DocType JSON files; understanding DocType structure, field types, or properties; troubleshooting schema issues; configuring naming, permissions, or child tables.  
**What it covers:** DocType JSON schema — core properties, field types (data, layout, relationship), field properties, naming conventions, child tables, single doctypes, best practices.

### frappe-hooks-expert
**When to use:** Implementing custom hooks; registering hooks in `hooks.py`; understanding hook execution order; extending Frappe with doc_events, scheduler tasks, UI customizations, or Jinja filters.  
**What it covers:** Frappe hooks system — application, installation, document events, permission, scheduler, UI, Jinja, request/job, safe execution, and other hooks; execution order; best practices; debugging.

### permissions-expert
**When to use:** Implementing custom permission logic; troubleshooting permission issues; working with `has_permission`, `permission_query_conditions`, `write_permission_query_conditions`, `has_website_permission`, workflow permission hooks, user permissions, share permissions, or permission levels.  
**What it covers:** Frappe permissions system — evaluation flow, all 7 extension hooks, user permissions, share permissions, permission levels, common patterns, debugging, testing, and migration guide.

### report-expert
**When to use:** Creating Script Reports, Query Reports, or understanding report structure; working with columns and filters; troubleshooting report issues.  
**What it covers:** Frappe reports — report types comparison, execute function, column/filter formats, creation workflow, advanced features (charts, summaries, custom buttons, tree reports), best practices.

### workflow-expert
**When to use:** Creating workflows; implementing workflow logic; understanding state transitions; configuring workflow actions or email notifications; using `before_transition`, `after_transition`, `filter_workflow_transitions`, or `has_workflow_action_permission` hooks.  
**What it covers:** Frappe Workflow system — structure, states, transitions, workflow actions, email notifications, all 5 extension hooks, permissions, common patterns, best practices, troubleshooting.

---

## DevOps & Infrastructure Skills

### bench-commands
**When to use:** Questions about bench CLI commands; site setup, app installation, backup/restore; database operations; migrations; development workflows in Frappe.  
**What it covers:** Comprehensive bench CLI reference — site management, app management, backup/restore, database operations, database maintenance, development operations, testing/debugging, job queue management, translation operations, utilities.

### frappe-ci-expert
**When to use:** Setting up GitHub Actions CI for Frappe apps; configuring database services for CI; running tests in CI; debugging CI failures.  
**What it covers:** CI/CD for Frappe — GitHub Actions workflow templates, MariaDB/PostgreSQL service configuration, bench setup in CI, helper scripts, test execution strategies, caching, debugging CI failures.

---

## Security Skills

### api-reviewer
**When to use:** Reviewing `@frappe.whitelist()` API security; checking for permission vulnerabilities; scanning for unprotected endpoints; validating role restrictions; auditing endpoints for security best practices.  
**What it covers:** API security review workflow — scanning with `scan_api_endpoints.py`, generating `docs/api-review.yaml`, reviewing `frappe.only_for()`, `frappe.has_permission()`, `frappe.get_list()` usage, and fixing vulnerabilities.

---

## Skill Management Skills

### skill-creator
**When to use:** Creating a new skill or updating an existing skill; designing SKILL.md with good descriptions, progressive disclosure, and bundled resources.  
**What it covers:** Skill creation process — understanding requirements, planning resources (scripts/references/assets), initializing with `init_skill.py`, editing SKILL.md, packaging with `package_skill.py`, iterating.

### skill-importer
**When to use:** Copying skills from remote GitHub repositories; maintaining the list of remote skill sources; updating local skills with fresh copies from upstream.  
**What it covers:** Skill import workflow — `assets/skill-sources.yaml` management, automated import via `import_skills.py`, manual import steps (clone, copy, clean up, verify), updating existing skills.
