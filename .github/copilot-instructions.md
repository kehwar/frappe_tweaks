# GitHub Copilot Instructions for frappe_tweaks

## Project Overview

This is a Frappe application that provides various tweaks and enhancements for the Frappe framework. The app extends core Frappe functionality including:
- Custom Client Scripts and Server Scripts
- Business Logic management
- Access Control (AC) rules and permissions
- Workflow enhancements
- Query report customizations
- Event scripts (**Note**: Event scripts will be deprecated soon)

## Technology Stack

- **Language**: Python 3.10+
- **Framework**: Frappe (ERPNext ecosystem)
- **Frontend**: JavaScript (Frappe's frontend framework)
- **Package Manager**: pip (Python), managed by bench

## Project Structure

```
tweaks/
├── config/          # Frappe configuration files
├── custom/          # Customizations to core Frappe doctypes
│   ├── doctype/    # Custom doctype implementations (Client Script, Server Script, etc.)
│   └── utils/      # Utility modules for customizations
├── hooks.py         # Frappe app hooks and configurations
├── patches/         # Database migration patches
├── public/          # Frontend assets (JS, CSS)
├── templates/       # Jinja templates
├── tweaks/          # Main app doctypes
│   └── doctype/    # Custom doctypes (Business Logic, AC Rules, etc.)
└── utils/           # Utility modules
```

## Development Environment

This is a Frappe app that must be installed within a Frappe bench environment. It cannot run standalone.

### Common Development Commands

```bash
# Create a new site
bench new-site development.localhost --admin-password admin --db-root-password 123

# Install the app
bench --site development.localhost install-app tweaks

# Uninstall the app
bench --site development.localhost uninstall-app tweaks --yes --no-backup

# Run migrations
bench --site development.localhost migrate

# Start development server
bench start

# Run a specific patch
bench --site development.localhost run-patch --force tweaks.patches.YYYY.patch_name

# Backup
bench --site development.localhost backup --backup-path "backups"

# Restore
bench --site development.localhost restore --db-root-password 123 "backups/backup-file.sql.gz"
```

## Code Conventions

### Python

- **Indentation**: 4 spaces (as defined in .editorconfig)
- **Import Style**: Standard library first, then Frappe imports, then local imports
- **Doctype Classes**: Inherit from `frappe.model.document.Document` or appropriate base classes
- **Naming**: 
  - Snake_case for functions and variables
  - PascalCase for classes
  - Use descriptive names that match Frappe conventions

### JavaScript

- **Indentation**: 4 spaces
- **Frontend Scripts**: 
  - Use `frappe.ui.form.on()` for form scripts
  - Use `frappe.listview_settings` for list view customizations
  - Follow Frappe's client-side API conventions

### File Organization

- **Test Files**: Named `test_<doctype_name>.py` in the same directory as the doctype
- **Hooks**: Defined in `hooks.py` at the root of the app
- **Patches**: Located in `patches/YYYY/` directories, named with date prefix
- **Custom Fields**: Created via `create_custom_fields()` utility

## Testing

- Tests use Frappe's test framework (`frappe.tests.utils.FrappeTestCase`)
- Test files are located alongside their corresponding doctypes
- Run tests using bench:
  ```bash
  bench --site development.localhost run-tests --app tweaks
  ```

## Frappe Framework Specifics

### Important Concepts

1. **DocTypes**: Core data models in Frappe. Each doctype has a JSON definition and optional Python controller
2. **Hooks**: Used to extend framework behavior (defined in `hooks.py`)
3. **Whitelisted Methods**: Use `@frappe.whitelist()` decorator for API endpoints
4. **Permissions**: Managed through Role-based and custom AC (Access Control) rules
5. **Patches**: Database migration scripts run during `bench migrate`

### Custom Implementations

This app customizes several core Frappe doctypes:
- **Client Script**: Extended via `TweaksClientScript` class
- **Server Script**: Extended via `TweaksServerScript` class  
- **Reminder**: Extended via `TweaksReminder` class

These customizations are registered in `hooks.py` under `override_doctype_class` hook.

**Note**: The app uses some monkey patches (e.g., `Document.run_method` in `tweaks/custom/doctype/document.py`, `FormMeta.add_custom_script` in `tweaks/custom/doctype/client_script.py`) that directly modify framework classes. The app will soon move away from these monkey patches to use custom hooks from a forked Frappe/ERPNext version instead.

## Important Notes

- Always test changes in a development site before production
- Use patches for schema changes or data migrations
- Follow Frappe's permission model - don't bypass security checks
- Custom scripts (Client/Server) should be enabled via settings
- The app integrates with ERPNext for pricing rules and other features

## API and Integration Points

- **Permission Hooks**: Custom permission logic in `permission_hooks`
- **Event Scripts**: Dynamic event handling system (**Note**: Will be deprecated soon)
- **Pricing Rules**: Custom discount and pricing logic
- **Workflow Scripts**: Custom workflow state change handlers
- **Query Reports**: PDF and Excel export customizations

## Common Patterns

### Creating a New Doctype

1. Use Frappe UI to create the doctype JSON
2. Add Python controller in `tweaks/tweaks/doctype/<doctype_name>/`
3. Add JavaScript controller if needed
4. Create test file `test_<doctype_name>.py`
5. Update `hooks.py` if special hooks are needed

### Adding Custom Fields

```python
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_fields():
    custom_fields = {
        "DocType Name": [
            {
                "fieldname": "custom_field",
                "fieldtype": "Data",
                "label": "Custom Field",
                # ... other properties
            }
        ]
    }
    create_custom_fields(custom_fields)
```

### Whitelisting API Methods

```python
import frappe

@frappe.whitelist()
def my_api_method(param1, param2):
    # Your logic here
    return result
```

## Dependencies

- Frappe Framework (version ~=15.0.0, managed by bench)
- Python >= 3.10
- Optional: ERPNext (for pricing rule integrations)

## Build and Installation

This app uses `flit` for packaging (see `pyproject.toml`). However, in practice:
- Apps are installed via `bench get-app` and `bench install-app`
- No separate build step is required
- Frontend assets are bundled by Frappe's build system

## Additional Resources

- Frappe Documentation: https://frappeframework.com/docs
- ERPNext Documentation: https://docs.erpnext.com
- Frappe Forum: https://discuss.frappe.io
