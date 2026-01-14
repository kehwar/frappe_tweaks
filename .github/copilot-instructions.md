# GitHub Copilot Instructions for frappe_tweaks

## Project Overview

This is a Frappe application that provides various tweaks and enhancements for the Frappe framework. The app extends core Frappe functionality including:
- Custom Client Scripts and Server Scripts
- Business Logic management
- Access Control (AC) rules and permissions
- Workflow enhancements
- Query report customizations
- Sync Job framework

## Technology Stack

- **Language**: Python 3.10+
- **Framework**: Frappe (ERPNext ecosystem)
- **Frontend**: JavaScript (Frappe's frontend framework)
- **Package Manager**: pip (Python), managed by bench

## Development Environment

This is a Frappe app that must be installed within a Frappe bench environment. It cannot run standalone.

## Code Style Guidelines

### Python

- **Formatter**: Use **black** formatter for Python code formatting
- **Indentation**: 4 spaces (PEP 8 compliant)
- **Import Style**: Standard library first, then Frappe imports, then local imports
- **Naming**: 
  - snake_case for functions and variables
  - PascalCase for classes
  - Use descriptive names that match Frappe conventions

### JavaScript

- **Indentation**: 4 spaces
- **Frontend Scripts**: 
  - Use `frappe.ui.form.on()` for form scripts
  - Use `frappe.listview_settings` for list view customizations
  - Follow Frappe's client-side API conventions

### Universal Rules

- Always use **4 spaces** for indentation in all files (Python, JavaScript, JSON, YAML, etc.)
- Never use tabs
- Follow existing code patterns in the repository

## Domain-Specific Knowledge

This project uses **skills** extensively to provide domain-specific guidance and expertise. Skills are specialized agents that help with specific areas of the codebase. 

**IMPORTANT**: Always check if relevant skills are available before working on tasks.

When working on any feature or debugging any issue, first consult the skills list to see if there's specialized knowledge available for that domain.

## Additional Resources

- Frappe Documentation: https://frappeframework.com/docs
- ERPNext Documentation: https://docs.erpnext.com
- Frappe Forum: https://discuss.frappe.io
