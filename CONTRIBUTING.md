# Contributing to Frappe Tweaks

Thank you for considering contributing to Frappe Tweaks! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Assume good intentions

## Getting Started

### Prerequisites

- Frappe Framework (version 15+)
- Python 3.10+
- Git
- Basic understanding of Frappe Framework

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/frappe_tweaks.git
   cd frappe_tweaks
   ```

2. **Add to Bench**
   ```bash
   bench get-app /path/to/frappe_tweaks
   bench --site development.localhost install-app tweaks
   ```

3. **Enable Developer Mode**
   ```bash
   bench --site development.localhost set-config developer_mode 1
   bench --site development.localhost clear-cache
   ```

4. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Project Structure

```
tweaks/
├── __init__.py              # App initialization
├── hooks.py                 # Frappe hooks
├── tweaks/                  # Main module
│   ├── doctype/            # Custom DocTypes
│   │   ├── ac_action/
│   │   ├── ac_principal/
│   │   ├── ac_resource/
│   │   ├── ac_rule/
│   │   ├── event_script/
│   │   └── business_logic/
│   └── utils/              # Utility functions
├── custom/                  # Framework extensions
│   ├── doctype/            # DocType customizations
│   └── utils/              # Utility extensions
├── patches/                 # Migration patches
├── public/                  # Frontend assets
├── config/                  # Configuration
└── templates/               # Jinja templates
```

## Coding Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use meaningful variable and function names
- Add docstrings to all functions and classes

### Example:

```python
def resolve_principals(self, debug=False):
    """
    Resolve principal definitions into executable conditions.
    
    Args:
        debug (bool): If True, include debug information in output
        
    Returns:
        list: List of resolved principal dictionaries with SQL or script conditions
    """
    allowed = set()
    denied = set()
    # Implementation...
    return principals
```

### Code Organization

- Keep functions focused and single-purpose
- Avoid deep nesting (max 3-4 levels)
- Use early returns to reduce complexity
- Extract complex logic into helper functions
- Use descriptive names over comments

### Error Handling

- Use `frappe.throw()` for user-facing errors with translatable messages
- Use `frappe.log_error()` for system errors
- Provide helpful error messages
- Log errors before throwing when appropriate

```python
if not self.document_type:
    frappe.throw(_("Document Type is required"))
```

### Comments and Documentation

- Write self-documenting code
- Add comments only when necessary to explain "why", not "what"
- Keep comments up to date with code changes
- Use TODO comments for future improvements (see TODOs section below)

## Making Changes

### 1. Feature Development

**Before coding:**
- Check existing issues and discussions
- Open an issue to discuss major changes
- Ensure the feature aligns with project goals

**While coding:**
- Write tests for new functionality
- Update documentation
- Follow coding guidelines
- Keep commits focused and atomic

**Example commit messages:**
```
feat: Add support for custom AC actions

- Add custom_action field to AC Action
- Update validation logic
- Add tests for custom actions

Fixes #123
```

### 2. Bug Fixes

**Process:**
1. Create a test that reproduces the bug
2. Fix the bug
3. Verify the test passes
4. Add regression test if needed

**Example commit message:**
```
fix: Prevent duplicate AC actions on save

- Add unique constraint validation
- Update error messages
- Add test for duplicate prevention

Fixes #456
```

### 3. Documentation

- Update README.md for user-facing changes
- Update ARCHITECTURE.md for architectural changes
- Add inline comments for complex logic
- Update docstrings when changing functions

### 4. Testing

**Running Tests:**
```bash
# All tests
bench --site development.localhost run-tests --app tweaks

# Specific module
bench --site development.localhost run-tests --app tweaks --module tweaks.tweaks.doctype.ac_rule.test_ac_rule

# With coverage
bench --site development.localhost run-tests --app tweaks --coverage
```

**Writing Tests:**
- Test files: `test_{doctype}.py`
- Use Frappe's test framework
- Test both success and failure cases
- Test edge cases and boundary conditions
- Clean up test data in tearDown

**Example:**
```python
def test_ac_rule_validation(self):
    """Test AC Rule requires at least one non-exception principal"""
    ac_rule = frappe.get_doc({
        "doctype": "AC Rule",
        "resources": [{"resource": "Test Resource", "exception": 0}],
        "principals": [{"principal": "Test Principal", "exception": 1}]
    })
    
    self.assertRaises(frappe.ValidationError, ac_rule.insert)
```

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commits are clean and well-described
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Follows coding guidelines

## Related Issues
Fixes #issue_number
```

### Review Process

1. Automated tests run on PR
2. Code review by maintainers
3. Address feedback and update PR
4. Approval and merge

### After Merge

- Delete your feature branch
- Close related issues
- Update changelog if needed

## Development Workflow

### Adding a New DocType

1. Create DocType in Frappe UI (developer mode)
2. Add Python controller: `tweaks/tweaks/doctype/{doctype}/{doctype}.py`
3. Implement validation logic
4. Add tests: `test_{doctype}.py`
5. Update hooks.py if needed
6. Document in README.md

### Adding a New Feature

1. Plan the feature (issue/discussion)
2. Design the architecture
3. Implement the feature
4. Write tests
5. Update documentation
6. Submit PR

### Creating a Patch

For database migrations:

1. Create file: `tweaks/patches/YYYY/YYYY_MM_DD__description.py`
2. Add to `patches.txt`
3. Implement patch function
4. Test on fresh install and upgrade

**Example patch:**
```python
import frappe

def execute():
    """Add new field to AC Rule"""
    if not frappe.db.exists("Custom Field", {"dt": "AC Rule", "fieldname": "new_field"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "AC Rule",
            "fieldname": "new_field",
            "label": "New Field",
            "fieldtype": "Data"
        }).insert()
```

## Optimization TODOs

When you notice code that could be optimized but don't want to refactor immediately, add a TODO comment:

```python
# TODO: Optimize query to use batch loading for better performance
# TODO: Cache result at site level instead of request level
# TODO: Consider using Redis for faster cache access
# TODO: This recursive call could be optimized with iteration
```

**Format:**
- Start with `# TODO:`
- Be specific about what could be improved
- Explain why it matters (performance, maintainability, etc.)
- Optional: Reference an issue number

## Common Tasks

### Adding TODOs for Optimization

When reviewing code, add TODO comments for:
- Database query optimizations (N+1 queries, missing indexes)
- Caching opportunities
- Algorithmic improvements
- Memory usage optimizations
- Redundant operations
- API call optimizations

### Debugging

```bash
# Enable debug mode
bench --site development.localhost set-config developer_mode 1

# Watch logs
bench --site development.localhost watch

# Console
bench --site development.localhost console

# SQL debugging
bench --site development.localhost mariadb
```

### Using the Console

```python
# In bench console
frappe.set_user("Administrator")
doc = frappe.get_doc("AC Rule", "RULE-001")
doc.resolve_principals(debug=True)
```

## Release Process

(For maintainers)

1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Create release branch
4. Test thoroughly
5. Merge to main
6. Create GitHub release
7. Tag version

## Getting Help

- **Documentation**: Check README.md and ARCHITECTURE.md
- **Issues**: Search existing issues or create new one
- **Discussions**: Use GitHub Discussions for questions
- **Code**: Read the code! It's well-documented

## Recognition

Contributors will be:
- Added to contributors list
- Mentioned in release notes
- Appreciated in the community!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Frappe Tweaks! 🎉
