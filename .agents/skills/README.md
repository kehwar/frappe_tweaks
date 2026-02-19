# Available Skills

This directory contains AI agent skills that provide specialized knowledge and guidance for working with this Frappe application. Each skill is a self-contained package that extends the AI assistant's capabilities in a specific domain.

## Summary

| Skill | Description |
|-------|-------------|
| [ac-rules-expert](#ac-rules-expert) | Fine-grained AC Rule access control system |
| [api-reviewer](#api-reviewer) | Security review of Frappe API endpoints |
| [bench-commands](#bench-commands) | Frappe bench CLI command reference |
| [doctype-schema-expert](#doctype-schema-expert) | DocType JSON schema structure and field types |
| [document-review-expert](#document-review-expert) | Document review/approval workflow system |
| [frappe-ci-expert](#frappe-ci-expert) | CI/CD setup with GitHub Actions |
| [frappe-hooks-expert](#frappe-hooks-expert) | Frappe hooks system extension points |
| [open-observe-api-expert](#open-observe-api-expert) | OpenObserve logging and observability integration |
| [permissions-expert](#permissions-expert) | Frappe permission system and custom permission hooks |
| [power-query-expert](#power-query-expert) | Power BI / Excel Power Query integration |
| [report-expert](#report-expert) | Frappe Script Reports and Query Reports |
| [skill-creator](#skill-creator) | Guide for creating and updating skills |
| [skill-importer](#skill-importer) | Import skills from remote GitHub repositories |
| [sync-job-expert](#sync-job-expert) | Queue-based Sync Job framework |
| [workflow-expert](#workflow-expert) | Frappe Workflow states, transitions, and actions |

---

## Access Control & Permissions

### ac-rules-expert

Expert guidance for the Frappe Tweaks AC Rule system — an advanced, rule-based access control framework that extends Frappe's built-in permissions with fine-grained, record-level control.

**Use when:** Working with AC Rules, Query Filters, AC Resources, AC Actions, implementing fine-grained access control, debugging permission issues, creating principal/resource filters, integrating with DocTypes or Reports, or understanding rule evaluation and SQL generation.

**Key concepts:** Permit/Forbid rule semantics, principal-based filtering (users, roles, user groups), resource-based targeting (doctypes, reports), SQL/Python/JSON filter modes.

---

### api-reviewer

Security review and analysis for Frappe API endpoints decorated with `@frappe.whitelist()`.

**Use when:** Reviewing API security, checking for permission vulnerabilities, scanning for unprotected endpoints, validating role restrictions, or auditing API endpoints for security best practices.

**Key checks:** Missing `frappe.only_for()`, using `frappe.get_all` instead of `frappe.get_list`, missing document permission checks.

---

### permissions-expert

Comprehensive guidance on Frappe's multi-layered permission system and its extension hooks.

**Use when:** Implementing custom permission logic, troubleshooting permission issues, understanding permission query conditions, working with child table permissions, virtual DocType permissions, workflow transition filtering, approval routing, or debugging access control problems.

**Covers:** `has_permission`, `permission_query_conditions`, `write_permission_query_conditions`, `has_website_permission`, `filter_workflow_transitions`, `has_workflow_action_permission`, role-based permissions, user permissions, share permissions, and permission levels.

---

## Framework & Development

### bench-commands

Comprehensive reference for the Frappe bench CLI covering all common development operations.

**Use when:** Working with bench commands, site setup, database operations, backup/restore procedures, MariaDB configuration, or common development workflows in Frappe.

**Covers:** Site management, app installation, backup/restore, database operations, migrations, scheduler, testing, and development workflows.

---

### frappe-ci-expert

Expert guidance for setting up CI/CD test pipelines for Frappe applications using GitHub Actions.

**Use when:** Setting up GitHub Actions workflows, configuring CI test environments, running tests in CI, setting up database services for CI, or automating tests for Frappe/ERPNext applications.

**Covers:** GitHub Actions workflow templates, MariaDB/PostgreSQL service containers, bench initialization, site creation, server script configuration, and test execution patterns.

---

### frappe-hooks-expert

Expert guidance on Frappe's hooks system — the primary mechanism for extending and customizing framework behavior without modifying core code.

**Use when:** Implementing custom hooks, understanding hook execution order, registering hooks in `hooks.py`, troubleshooting hook issues, or extending Frappe framework functionality.

**Covers:** Application hooks, document events (`doc_events`), permission hooks, scheduler hooks, UI hooks, Jinja filters, installation hooks, request/job hooks, and execution order.

---

## Data & Schema

### doctype-schema-expert

Expert guidance on Frappe DocType schemas — the JSON files that define database tables, form layouts, and business logic structure.

**Use when:** Creating or modifying DocType JSON files, understanding DocType structure, working with field definitions, configuring DocType properties, or troubleshooting schema-related issues.

**Covers:** JSON structure, all field types and their properties, naming conventions, permissions, child tables, and common patterns.

---

### report-expert

Expert guidance for creating Frappe reports with full programmatic control.

**Use when:** Creating Script Reports or Query Reports, understanding report structure, working with columns and filters, or troubleshooting report-related issues.

**Covers:** Report types (Script, Query, Report Builder), column and filter field types/properties, report creation workflow, and advanced features.

---

## Business Logic & Workflows

### document-review-expert

Expert guidance for the Frappe Tweaks Document Review system — a flexible, rule-based document validation and approval framework.

**Use when:** Working with Document Review Rules, Document Reviews, implementing review/approval workflows, creating validation scripts, debugging review issues, understanding review evaluation and lifecycle, or integrating reviews with workflows and submissions.

**Key concepts:** Python validation scripts, automatic form banners, submission blocking, workflow integration, permission-aware display.

---

### sync-job-expert

Expert guidance for the Frappe Tweaks Sync Job framework — a queue-based system for data synchronization between DocTypes.

**Use when:** Working with Sync Job Types, Sync Job controllers, enqueueing sync jobs, debugging sync job issues, implementing sync logic, or understanding sync job lifecycle and hooks.

**Key concepts:** Sync Job Type (template), Sync Job (instance), controller modules, Bypass vs. Standard mode, retry configuration.

---

### workflow-expert

Expert guidance on Frappe's Workflow system for document state management with configurable approval processes.

**Use when:** Creating workflows, implementing workflow logic, understanding state transitions, working with workflow actions, configuring email notifications, or troubleshooting workflow-related issues.

**Covers:** Workflow states and transitions, role-based transition permissions, `before_transition`/`after_transition` hooks, `filter_workflow_transitions`, `has_workflow_action_permission`, email notifications, and workflow action records.

---

## Integrations

### open-observe-api-expert

Expert guidance for the OpenObserve API integration — connecting Frappe applications to the OpenObserve observability platform for logging, monitoring, and tracing.

**Use when:** Creating or configuring the Open Observe API DocType, implementing `send_logs()` or `search_logs()`, integrating with Server Scripts/Business Logic/Client-side code, debugging connection issues, or implementing logging, monitoring, error tracking, performance metrics, or audit trail use cases.

**Safe exec access:** `open_observe.send_logs()`, `open_observe.search_logs()`

---

### power-query-expert

Expert guidance for connecting Microsoft Power Query (Power BI, Excel) to Frappe apps and reports.

**Use when:** Building Power Query M code for Frappe data access, integrating Frappe reports with Power BI/Excel, implementing authentication, handling long-running reports with the `report_long_polling` API to avoid timeouts, or troubleshooting Power Query caching and connection issues.

**Covers:** REST API connections, long-polling API for heavy reports, authentication, column type transformations, and troubleshooting.

---

## Skill Management

### skill-creator

Guide for creating effective AI agent skills that provide specialized knowledge, workflows, and tool integrations.

**Use when:** Creating a new skill or updating an existing skill to extend AI assistant capabilities with domain-specific knowledge.

**Covers:** Skill anatomy (SKILL.md, scripts, references, assets), progressive disclosure design, writing effective descriptions, bundling resources, and the full creation/iteration workflow.

---

### skill-importer

Imports and synchronizes skills from remote GitHub repositories into this repository's `.agents/skills/` directory.

**Use when:** Copying skills from other repositories, maintaining remote skill sources, or updating local skills with fresh copies from upstream.

**Covers:** `assets/skill-sources.yaml` configuration, automated import script, manual import steps, and update workflows.
