## Tweaks

Tweaks for Frappe

### Documentation

**Start here:** [Documentation Index](INDEX.md) - Complete guide to all documentation

- **[Monkeypatch Migration Guide](MONKEYPATCH_MIGRATION.md)** - Comprehensive guide for migrating monkeypatches to a Frappe/ERPNext fork
- **[Monkeypatch Quick Reference](MONKEYPATCH_SUMMARY.md)** - Quick lookup table for all monkeypatches
- **[Architecture Diagrams](ARCHITECTURE.md)** - Visual flow charts and system architecture

### Features

This app provides several enhancements to core Frappe/ERPNext functionality:

- **Server Script Enhancements**: Priority-based execution, additional event types (Permission Policy, Permission Query), and extended metadata
- **Workflow Auto-Apply**: Automatic workflow transitions based on conditions
- **Permission Policies**: Advanced permission system using Server Scripts
- **Document Event Extensions**: Enhanced event handling with method argument access
- **Database Query Optimizations**: Performance improvements for permission queries
- **Pricing Rule Dynamics**: Scriptable pricing rules for complex business logic (ERPNext)

### Migration to Frappe/ERPNext Fork

If you're maintaining a fork of Frappe/ERPNext, you can migrate the monkeypatches in this app directly into your fork. See the [Migration Guide](MONKEYPATCH_MIGRATION.md) for detailed instructions.

#### License

mit