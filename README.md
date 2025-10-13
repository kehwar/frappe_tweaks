# Frappe Tweaks

A comprehensive Frappe app that extends and enhances the Frappe Framework with advanced features including custom access control, event scripting, business logic management, workflow automation, and powerful customizations for server scripts, client scripts, and more.

## Features

### 1. **Access Control System (AC Module)**
Advanced role-based access control with hierarchical rules:
- **AC Principal**: Define users, roles, user groups, or custom scripts as principals
- **AC Resource**: Define DocTypes, Reports, or custom resources with field-level access
- **AC Rule**: Create complex access rules combining principals and resources
- **AC Action**: Standard actions (Read, Write, Create, Delete, Submit, Cancel, etc.)
- Supports nested hierarchies for both principals and resources
- SQL and Python scripting for dynamic conditions

### 2. **Event Script System**
Execute custom scripts on document lifecycle events:
- Trigger scripts on document events (before_save, after_save, validate, etc.)
- Support for workflow transitions (before_transition, after_transition)
- Permission-based events (has_permission, has_field_permission)
- User/role/group filtering
- Priority-based execution order
- Parameter passing from other documents
- Comprehensive script caching system

### 3. **Business Logic Management**
Organize and manage business logic:
- **Business Logic**: Central repository for business rules and logic
- **Business Logic Category**: Categorize logic by function/domain
- **Business Logic Link**: Link business logic to documents
- Auto-naming with category-based series
- Track document relationships

### 4. **DocType Groups**
Group related DocTypes for easier management:
- Create logical groupings of DocTypes
- Apply event scripts to entire groups
- Simplify permission management across related DocTypes

### 5. **Enhanced Server Scripts**
Extended server script capabilities:
- Title field for better organization
- Reference script linking
- Priority-based execution
- Description field for documentation
- Additional event types
- Hash-based auto-naming

### 6. **Enhanced Client Scripts**
Improved client-side scripting with additional features and customizations.

### 7. **Enhanced Workflows**
Extended workflow functionality:
- Auto-apply transitions based on conditions
- Custom transition logic
- Enhanced workflow state management

### 8. **Custom Patches and Extensions**
- Authentication patches
- Database query enhancements
- Fixture management improvements
- Safe execution environment extensions (regex, cache modules, etc.)
- Virtual DocType support
- Enhanced permissions system

### 9. **Utility Functions**
- Query report utilities
- Groupby operations
- Changelog tracking
- Access control helpers
- Preflight checks

## Installation

### Prerequisites
- Frappe Framework (version 15+)
- Python 3.10+

### Install via Bench

```bash
# Get the app
bench get-app https://github.com/kehwar/frappe_tweaks.git

# Install on your site
bench --site [sitename] install-app tweaks

# Migrate the site
bench --site [sitename] migrate
```

## Configuration

The app applies various patches on initialization. No additional configuration is required for basic functionality.

## Usage

### Creating an Access Control Rule

1. Navigate to **AC Principal** and create principals (users, roles, groups)
2. Navigate to **AC Resource** and define resources (DocTypes, Reports, Custom)
3. Navigate to **AC Rule** and create rules combining principals and resources
4. Specify actions (Read, Write, Create, Delete, etc.)

### Creating an Event Script

1. Navigate to **Event Script**
2. Select the Document Type or Document Type Group
3. Choose the event (e.g., before_save, after_save, validate)
4. Write your Python script
5. Set priority (higher numbers execute first)
6. Optionally filter by user/role/group

### Using Business Logic

1. Create a **Business Logic Category**
2. Create **Business Logic** entries with your rules
3. Link business logic to documents using **Business Logic Link**

### Enhanced Server Scripts

Server Scripts now support:
- **Title**: Better identification in lists
- **Reference Script**: Link to other scripts
- **Priority**: Control execution order for DocType Events
- **Description**: Document your script's purpose

## Architecture

The app is organized into several modules:

- **`tweaks/tweaks/doctype/`**: Core DocTypes (AC module, Event Scripts, Business Logic)
- **`tweaks/custom/`**: Patches and extensions to Frappe core (Server Scripts, Workflows, etc.)
- **`tweaks/utils/`**: Utility functions and helpers
- **`tweaks/patches/`**: Database patches for migrations
- **`tweaks/config/`**: Configuration files
- **`tweaks/public/`**: Frontend assets

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Development

### Code Structure

```
tweaks/
├── __init__.py           # App initialization and patch application
├── hooks.py              # Frappe hooks configuration
├── tweaks/               # Main app module
│   ├── doctype/          # Custom DocTypes
│   │   ├── ac_action/
│   │   ├── ac_principal/
│   │   ├── ac_resource/
│   │   ├── ac_rule/
│   │   ├── event_script/
│   │   └── business_logic/
│   └── utils/            # Utility functions
├── custom/               # Frappe core extensions
│   ├── doctype/          # DocType customizations
│   │   ├── server_script_customization.py
│   │   ├── workflow.py
│   │   └── client_script.py
│   └── utils/            # Utility extensions
│       ├── safe_exec.py
│       ├── permissions.py
│       └── authentication.py
└── patches/              # Migration patches
```

### Running Tests

```bash
# Run all tests
bench --site [sitename] run-tests --app tweaks

# Run specific test
bench --site [sitename] run-tests --app tweaks --module tweaks.tweaks.doctype.ac_rule.test_ac_rule
```

## API

Key whitelisted methods:

- `tweaks.tweaks.doctype.event_script.event_script.get_resolved_script_map`
- `tweaks.tweaks.doctype.event_script.event_script.inspect_permissions`
- `tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_rule_map`
- `tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_resource_rules`

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License

Copyright (c) 2025, Erick W.R.

See [license.txt](license.txt) for details.

## Credits

- Developed by Erick W.R.
- Built on the Frappe Framework

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/kehwar/frappe_tweaks/issues).