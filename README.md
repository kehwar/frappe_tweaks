## Tweaks

[![CI](https://github.com/kehwar/frappe_tweaks/actions/workflows/ci.yml/badge.svg)](https://github.com/kehwar/frappe_tweaks/actions/workflows/ci.yml)

Tweaks for Frappe

## Features

### AC Rule System

Advanced access control framework providing fine-grained, rule-based permissions for Frappe applications.

- **Record-level permissions**: Control access at the individual record level
- **Dynamic filtering**: Use SQL, Python, or JSON filters
- **Rule-based logic**: Permit/Forbid semantics for complex access patterns
- **Principal & Resource filtering**: Control who can access what
- **Action-based control**: Manage specific operations (read, write, delete, etc.)

📖 **Documentation**: [AC Rule System Guide](docs/ac-rule-system.md)

### Query Filter

Reusable filter definitions for access control and data filtering.

- **Multiple filter types**: JSON, SQL, and Python filters
- **Reusable across rules**: Create once, use in multiple AC Rules
- **Safe execution**: Python filters run in sandboxed environment
- **SQL generation**: Automatic conversion to optimized SQL queries

### Other Features

- **Custom Client Scripts**: Enhanced client-side scripting
- **Server Scripts**: Server-side business logic execution
- **Business Logic Management**: Centralized business logic repository
- **Workflow Enhancements**: Extended workflow capabilities
- **Query Report Customizations**: Enhanced reporting features
- **Sync Job Framework**: Queue-based data synchronization system

## Documentation

- [AC Rule System](docs/ac-rule-system.md) - Complete guide to the access control system
- [Developer Instructions](.github/instructions/) - Detailed instructions for developers

## Installation

```bash
bench get-app tweaks
bench --site [site-name] install-app tweaks
```

## Development

This app requires Frappe Framework (v15+) and Python 3.10+.

### Setup Development Environment

```bash
# Get the app
bench get-app https://github.com/kehwar/frappe_tweaks

# Install on a site
bench --site development.localhost install-app tweaks

# Start development
bench start
```

### Running Tests

```bash
bench --site development.localhost run-tests --app tweaks
```

## Contributing

Contributions are welcome! Please ensure:

- Follow the coding conventions (4-space indentation)
- Write tests for new features
- Update documentation
- Follow the instructions in `.github/instructions/`

## License

MIT