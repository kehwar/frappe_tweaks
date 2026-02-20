---
name: frappe-tweaks-translation-helper
description: Helper utilities for finding, validating, and managing translations in Frappe apps. Includes commands for finding untranslated strings and translation file locations. Use when working with PO/POT files, finding untranslated strings, or validating translation completeness.
---

# Translation Helper

## Finding Missing Translations

### By Context
```bash
# List untranslated strings for specific context
cd /workspace/development/frappe-bench/apps/<app_name>
awk '/msgctxt "ContextName"/{getline; msgid=$0; getline; if($0 ~ /msgstr ""$/) print msgid}' <app_name>/locale/es_PE.po

# Example: Number system context
awk '/msgctxt "Number system"/{getline; msgid=$0; getline; if($0 ~ /msgstr ""$/) print msgid}' <app_name>/locale/es_PE.po
```

### By Module/File
```bash
# Find untranslated strings from specific file
grep -A 2 "path/to/file.py" <app_name>/locale/es_PE.po | grep -A 1 'msgstr ""$'
```

### All Untranslated
```bash
# Find all empty msgstr entries
grep -B 1 'msgstr ""$' <app_name>/locale/es_PE.po | grep msgid

# Count total untranslated
grep 'msgstr ""$' <app_name>/locale/es_PE.po | wc -l
```

## Translation File Locations

For any Frappe app:
- **POT template**: `apps/<app_name>/<app_name>/locale/main.pot`
- **PO translations**: `apps/<app_name>/<app_name>/locale/es_PE.po`
- **MO compiled**: `apps/<app_name>/<app_name>/locale/es_PE.mo`

**Pattern**: `apps/{app_name}/{app_name}/locale/{locale}.{extension}`

## Validation Commands

```bash
# Verify PO file syntax
msgfmt --check <app_name>/locale/es_PE.po

# Check for fuzzy translations (need review)
grep -c '#, fuzzy' <app_name>/locale/es_PE.po

# Find fuzzy entries
grep -B 2 '#, fuzzy' <app_name>/locale/es_PE.po | grep msgid
```

## Quick Reference: Translation Workflow

```bash
cd /workspace/development/frappe-bench

# 1. Generate POT (extract strings from code)
bench --site development.localhost generate-pot-file --app <app_name>

# 2. Update PO (merge new strings)
bench --site development.localhost update-po-files --app <app_name> --locale es_PE

# 3. Find untranslated (identify what needs translation)
cd apps/<app_name>
awk '/msgstr ""$/{print NR": "$0}' <app_name>/locale/es_PE.po | head -20

# 4. Edit PO file (add translations manually)
# Edit <app_name>/locale/es_PE.po

# 5. Compile (convert to binary)
cd /workspace/development/frappe-bench
bench --site development.localhost compile-po-to-mo --app <app_name>

# 6. Deploy
bench --site development.localhost build-message-files && bench clear-cache
```

## Critical Notes

1. **Context is important**: Same English string can have different translations based on context
   - Example: "Journal Entry" in accounting vs "Entry" in general context

2. **Always update POT first**: Before updating PO files, regenerate POT to capture new strings from code changes

3. **Locale format**: Use underscores `es_PE`, not hyphens `es-PE`

4. **File encoding**: PO files must be UTF-8 encoded

5. **Special characters**:
   - Use proper Unicode escapes (e.g., `\u00ed` for í) OR
   - Raw UTF-8 characters (preferred for readability)
   - Examples: "Días" or "D\u00edas"

6. **Empty vs Missing**:
   - `msgstr ""` means string exists but not translated
   - Missing entry means string not extracted from code (need to regenerate POT)

7. **Context syntax in code**:
   ```python
   # Python
   _("text", context="Context Name")

   # JavaScript
   __("text", { context: "Context Name" })
   ```

## Common Issues

### Issue: Translations not showing in UI
**Solution**:
```bash
# Clear cache and rebuild
bench --site development.localhost build-message-files
bench clear-cache
```

### Issue: New strings not appearing in PO file
**Solution**: Regenerate POT first
```bash
bench --site development.localhost generate-pot-file --app <app_name>
bench --site development.localhost update-po-files --app <app_name> --locale es_PE
```

### Issue: MO file outdated
**Solution**: Recompile
```bash
bench --site development.localhost compile-po-to-mo --app <app_name> --force
```

## Integration with bench-commands Skill

For detailed bench command syntax and options, see the `bench-commands` skill, specifically:
- `references/translation-operations.md` - Complete translation workflow
- Quick translation update commands
- CSV to PO migration (for legacy apps)
