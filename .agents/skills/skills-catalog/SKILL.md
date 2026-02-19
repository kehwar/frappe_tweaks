---
name: skills-catalog
description: Complete catalog and navigation guide for all skills available in this project. Use when asked to summarize available skills, discover which skill to use for a task, get an overview of project capabilities, or when unsure which specialized skill applies to a request.
---

# Skills Catalog

Directory of all skills available in this Frappe Tweaks project, with descriptions and guidance on when to use each one.

## Frappe Framework Skills

### `frappe-hooks-expert`
Expert guidance on the Frappe hooks system (`hooks.py`): `doc_events`, permission hooks, scheduler hooks, UI hooks, Jinja filters, installation hooks, and other extension points.

**Use when:** implementing or troubleshooting hooks, registering `doc_events`, understanding hook execution order, or extending Frappe framework functionality.

---

### `frappe-ci-expert`
Expert guidance for setting up CI/CD tests for Frappe apps using GitHub Actions.

**Use when:** setting up GitHub Actions workflows, configuring database services for CI, running tests in CI environments, or debugging CI failures.

---

### `doctype-schema-expert`
Expert guidance on Frappe DocType JSON schemas: field types, properties, naming conventions, and best practices.

**Use when:** creating or modifying DocType JSON files, understanding DocType structure, working with field definitions, or troubleshooting schema-related issues.

---

### `report-expert`
Expert guidance on Frappe reports: Script Reports, Query Reports, columns, filters, and best practices.

**Use when:** creating Script or Query Reports, defining columns/filters, understanding report structure, or troubleshooting report issues.

---

### `workflow-expert`
Expert guidance on Frappe Workflows: states, transitions, workflow actions, email notifications, and extension hooks (`before_transition`, `after_transition`, `filter_workflow_transitions`, `has_workflow_action_permission`).

**Use when:** creating or configuring workflows, implementing workflow logic, working with workflow actions, or troubleshooting workflow issues.

---

### `permissions-expert`
Expert guidance on Frappe's permission system: `has_permission`, `permission_query_conditions`, `write_permission_query_conditions`, `has_website_permission`, role-based permissions, user permissions, share permissions, and workflow permission hooks.

**Use when:** implementing custom permission logic, troubleshooting access issues, working with permission query conditions, or debugging access control problems.

---

### `bench-commands`
Comprehensive reference for Frappe bench CLI: site management, app installation, backup/restore, database operations, migrations, and development workflows.

**Use when:** running bench commands, managing sites, restoring backups, running migrations, or performing development operations.

---

## Frappe Tweaks Custom Features

### `ac-rules-expert`
Expert guidance for the AC (Access Control) Rule system in Frappe Tweaks — a fine-grained, rule-based permission system built on top of Frappe's native permissions.

**Use when:** working with AC Rules, Query Filters, AC Resources, AC Actions, implementing record-level access control, or debugging AC permission issues.

---

### `document-review-expert`
Expert guidance for the Document Review system in Frappe Tweaks — a flexible rule-based document review/approval framework.

**Use when:** working with Document Review Rules, implementing approval workflows, creating validation scripts, debugging review issues, or integrating reviews with workflows/submissions.

---

### `sync-job-expert`
Expert guidance for the Sync Job framework in Frappe Tweaks — a queue-based system for data synchronization between DocTypes.

**Use when:** working with Sync Job Types, implementing sync logic, enqueueing sync jobs, or debugging sync job issues.

---

### `open-observe-api-expert`
Expert guidance for the OpenObserve API integration in Frappe Tweaks — logging and observability for Frappe applications.

**Use when:** configuring the OpenObserve API DocType, implementing `send_logs()`/`search_logs()`, integrating with Server Scripts or Business Logic, or debugging logging issues.

---

### `power-query-expert`
Expert guidance for connecting Microsoft Power Query (Power BI, Excel) to Frappe apps and reports.

**Use when:** building Power Query M code for Frappe data access, integrating Frappe reports with Power BI/Excel, handling long-running reports with `report_long_polling`, or troubleshooting Power Query connections.

---

## Security & API Skills

### `api-reviewer`
Security review for Frappe API endpoints decorated with `@frappe.whitelist()`: identifying missing permission checks, unprotected endpoints, and SQL injection risks.

**Use when:** auditing API security, checking for permission vulnerabilities, scanning for unprotected endpoints, or validating role restrictions.

---

## Skill Management Skills

### `skill-creator`
Guide for creating and updating skills: structure, design patterns, bundled resources, and packaging.

**Use when:** creating a new skill or updating an existing one.

---

### `skill-importer`
Import and synchronize skills from remote GitHub repositories.

**Use when:** copying skills from other repositories, maintaining upstream skill sources, or updating local skills from upstream.

---

## Quick Selection Guide

| Task | Skill to use |
|------|-------------|
| Register a `doc_event` or hook in `hooks.py` | `frappe-hooks-expert` |
| Create or modify a DocType JSON | `doctype-schema-expert` |
| Build a Script or Query Report | `report-expert` |
| Configure a Workflow | `workflow-expert` |
| Implement custom permissions | `permissions-expert` |
| Run bench commands / restore backup | `bench-commands` |
| Set up GitHub Actions CI | `frappe-ci-expert` |
| Work with AC Rules (record-level access) | `ac-rules-expert` |
| Add document approval/review logic | `document-review-expert` |
| Sync data between DocTypes | `sync-job-expert` |
| Send logs to OpenObserve | `open-observe-api-expert` |
| Connect Power BI/Excel to Frappe | `power-query-expert` |
| Audit API endpoint security | `api-reviewer` |
| Create or update a skill | `skill-creator` |
| Import a skill from another repo | `skill-importer` |
