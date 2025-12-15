# Documentation Index

This directory contains comprehensive documentation for migrating `frappe_tweaks` monkeypatches to a Frappe/ERPNext fork.

## Quick Navigation

### 📚 Start Here
- **[README.md](README.md)** - Project overview and features

### 🔧 For Migration
- **[MONKEYPATCH_SUMMARY.md](MONKEYPATCH_SUMMARY.md)** - Quick reference table (start here for overview)
- **[MONKEYPATCH_MIGRATION.md](MONKEYPATCH_MIGRATION.md)** - Complete migration guide (detailed instructions)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture diagrams and flow charts

## Reading Path

### If you want a quick overview:
1. Read **MONKEYPATCH_SUMMARY.md** (5 min read)
   - See the table of all patches
   - Understand priorities
   - Get file locations

### If you're ready to migrate:
1. Start with **MONKEYPATCH_SUMMARY.md** 
2. Then read **MONKEYPATCH_MIGRATION.md** for each patch you're migrating
3. Reference **ARCHITECTURE.md** to understand relationships and flows

### If you want to understand the architecture:
1. Read **ARCHITECTURE.md** first
2. Then dive into **MONKEYPATCH_MIGRATION.md** for implementation details

## Document Purpose

| Document | Purpose | Audience | Time to Read |
|----------|---------|----------|--------------|
| README.md | Project overview | Everyone | 2 min |
| MONKEYPATCH_SUMMARY.md | Quick lookup and migration order | Developers | 5 min |
| MONKEYPATCH_MIGRATION.md | Detailed migration instructions | Developers migrating code | 30 min |
| ARCHITECTURE.md | System design and flow diagrams | Architects and senior developers | 15 min |

## Key Sections

### MONKEYPATCH_SUMMARY.md
- ✅ At-a-glance table of all patches
- ✅ Migration priority order
- ✅ Quick commands and examples
- ✅ Files to delete after migration

### MONKEYPATCH_MIGRATION.md
- ✅ Inventory of all 11 patches
- ✅ Current implementation details
- ✅ Migration strategies (direct or hook-based)
- ✅ Files to modify in Frappe/ERPNext
- ✅ Custom fields to add
- ✅ Testing strategies
- ✅ Migration checklist
- ✅ Backward compatibility

### ARCHITECTURE.md
- ✅ Visual architecture diagrams
- ✅ Current vs. future flow charts
- ✅ Workflow enhancement flows
- ✅ Permission policy flows
- ✅ Server script details
- ✅ Dependency graphs
- ✅ File relationships
- ✅ Integration points

## Monkeypatch Categories

### Core Functionality (HIGH Priority)
1. Server Script enhancements
2. Document.run_method extension
3. Workflow auto-apply

### Performance & Features (MEDIUM Priority)
4. Database query caching
5. Permission policies
6. Server Script class override

### Quality of Life (LOW Priority)
7. Authentication fallback
8. User Group rename
9. Role rename
10. Reminder override
11. Pricing rules (ERPNext)

## Migration Workflow

```
1. Read MONKEYPATCH_SUMMARY.md
   └─> Understand what needs to be migrated

2. For each patch (in priority order):
   ├─> Read details in MONKEYPATCH_MIGRATION.md
   ├─> Check flows in ARCHITECTURE.md (if needed)
   ├─> Implement in your Frappe fork
   ├─> Test thoroughly
   └─> Mark as complete

3. After all migrations:
   ├─> Remove patches from frappe_tweaks
   ├─> Add backward compatibility checks
   ├─> Test with both old and new Frappe
   └─> Deploy to staging/production
```

## Getting Help

Each document includes:
- Specific file locations
- Code examples
- Migration strategies
- Testing recommendations

If you need clarification on a specific monkeypatch:
1. Check the detailed section in MONKEYPATCH_MIGRATION.md
2. Review the flow diagram in ARCHITECTURE.md
3. Look at the source code in `tweaks/custom/`

## Files Inventory

**Created Documentation:**
- ✅ MONKEYPATCH_SUMMARY.md (142 lines, quick reference)
- ✅ MONKEYPATCH_MIGRATION.md (617 lines, detailed guide)
- ✅ ARCHITECTURE.md (319 lines, diagrams and flows)
- ✅ README.md (updated with links)
- ✅ INDEX.md (this file)

**Source Files Referenced:**
- `tweaks/__init__.py` - Entry point
- `tweaks/custom/patches.py` - Patch orchestrator
- `tweaks/custom/doctype/*.py` - Doctype patches
- `tweaks/custom/utils/*.py` - Utility patches

## Version Information

This documentation is for:
- frappe_tweaks: v0.0.1
- Frappe: ~15.0.0
- ERPNext: Compatible version

Last updated: 2025-12-15
