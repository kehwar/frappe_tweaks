---
description: 'Guidelines for TODO and implementation tracking in the frappe_tweaks project'
applyTo: 'docs/todo/**'
---

# TODO and Implementation Tracking Guidelines

Instructions for tracking current and future implementations, tasks, and improvements for the frappe_tweaks project.

## Project Context

- **Purpose**: Central location for development planning and task tracking
- **Location**: `docs/todo/` directory
- **File Format**: Markdown with clear task checklists
- **Target Audience**: Project maintainers and contributors

## Purpose

The `docs/todo/` directory serves as the central location for:
- Tracking ongoing development tasks
- Planning future feature implementations
- Documenting technical debt and improvements
- Managing project roadmap items

## Conventions

### Task File Format

Each task file in `docs/todo/` should start with a YAML frontmatter block containing task properties:

```yaml
---
status: 'In Progress'
priority: 'High'
description: 'Brief description of the task or feature'
creation: '2026-01-01'
modified: '2026-01-02'
completed: ''
---
```

**Frontmatter Fields:**
- **status**: Current state (Planned, In Progress, Blocked, Completed, Deprecated)
- **priority**: Priority level (High, Medium, Low)
- **description**: Clear description of the task or feature
- **creation**: Date when the task was created (YYYY-MM-DD format)
- **modified**: Date when the task was last modified (YYYY-MM-DD format)
- **completed**: Date when the task was completed (YYYY-MM-DD format, empty if not completed)

### Task Tracking Format

- Use `[ ]` for pending tasks
- Use `[x]` for completed tasks
- Add dates when marking tasks as completed (format: YYYY-MM-DD)
- Include relevant file paths and line numbers when applicable
- Keep descriptions clear and actionable

### Task Organization

#### Priority Levels

Tasks should be organized by priority:
- **High Priority**: Critical features, security issues, or blocking bugs
- **Medium Priority**: Important improvements and documentation
- **Low Priority**: Nice-to-have features and optimizations

#### Status Values

Common status values:
- **Planned**: Task is defined but work hasn't started
- **In Progress**: Task is currently being worked on
- **Blocked**: Task is blocked by dependencies or issues
- **Completed**: Task is finished
- **Deprecated**: Task is no longer relevant

#### Task Structure

After the frontmatter block, structure your task content:

```markdown
# Task Name

Brief overview of the task (optional if description in frontmatter is sufficient)

## Tasks

- [ ] Subtask 1
  - Additional details if needed
- [ ] Subtask 2
- [x] Completed subtask (YYYY-MM-DD)

## Notes

Additional context, decisions, or links to related resources
```

### Documentation Guidelines

- Update TODO files regularly as tasks progress
- Each major feature should have its own detailed TODO file if needed
- Use TODO files as a reference for sprint planning and prioritization
- Link related GitHub issues and pull requests where applicable
- Include file paths and locations for code references

### File Naming

- Main tracking file: `README.md` (in `docs/todo/`)
- Feature-specific files: `feature-name-todo.md` (if needed)
- Keep file names lowercase with hyphens

### Archiving Completed Tasks

- Non-pending (completed, deprecated, or obsolete) tasks should be moved to `docs/todo/archive/`
- Maintain the original filename when moving to archive
- Update the `completed` date in the frontmatter before archiving
- Archive tasks periodically to keep the main `docs/todo/` directory focused on active work

## Best Practices

1. **Keep It Updated**: Regularly update task status to reflect current progress
2. **Be Specific**: Include enough detail for others to understand the task
3. **Link Resources**: Reference related issues, PRs, and documentation
4. **Archive Completed Work**: Move completed items to a "Completed Items" section
5. **Use Sections**: Organize tasks by priority or feature area
6. **Add Context**: Include relevant background information for complex tasks
7. **Track Dependencies**: Note when tasks depend on other tasks or external factors

## Common Task Categories

### Test Infrastructure
- Setting up CI/CD pipelines
- Creating and maintaining test files
- Configuring test coverage reporting
- Test framework setup and conventions

### Documentation
- Feature documentation
- API documentation
- Developer setup guides
- Deployment procedures
- Architecture documentation

### Code Quality
- Linting and formatting setup
- Pre-commit hooks
- Code review processes
- Contributing guidelines

### Feature Development
- New feature implementations
- Feature enhancements
- Deprecation planning
- Performance optimizations

## Related Documentation

- Main Instructions: `.github/copilot-instructions.md`
- Sync Job Framework: Use the `sync-job-expert` skill (`.github/skills/sync-job-expert/`)
- OpenObserve API: `.github/instructions/open-observe-api.instructions.md`
- Instructions Guidelines: `.github/instructions/instructions.instructions.md`

## Examples

### Example Task File

A complete task file (`test-infrastructure-overhaul.md`) would look like:

```markdown
---
status: 'In Progress'
priority: 'High'
description: 'Clean up and recreate test files with proper CI/CD integration'
creation: '2026-01-01'
modified: '2026-01-02'
completed: ''
---

# Test Infrastructure Overhaul

This task focuses on improving the test infrastructure with better organization and CI/CD integration.

## Tasks

- [x] Delete all current test files in the repository (2026-01-01)
  - Location: `tweaks/tweaks/doctype/*/test_*.py`
  - Location: `tweaks/tweaks/sync_job_type/*/test_*.py`
  - Reason: Test files will be recreated with improved structure and coverage

- [ ] Implement GitHub Actions CI workflow
  - [ ] Create `.github/workflows/tests.yml` for automated testing
  - [ ] Configure test environment with Frappe bench setup
  - [ ] Add test job for Python unit tests
  - [ ] Add linting job (if applicable)
  - [ ] Configure test coverage reporting
  - [ ] Add status badge to README.md

- [ ] Recreate test files with improved structure
  - [ ] Follow Frappe test framework best practices
  - [ ] Ensure proper test isolation
  - [ ] Add comprehensive test coverage for core features
  - [ ] Document testing conventions in main instructions

## Notes

- Test files should follow Frappe test framework conventions
- All tests must be isolated and not depend on execution order
- Coverage reporting will help identify gaps
```

### Example Completed Task Section

When a task is completed, update the frontmatter:

```markdown
---
status: 'Completed'
priority: 'High'
description: 'Clean up and recreate test files with proper CI/CD integration'
creation: '2026-01-01'
modified: '2026-02-15'
completed: '2026-02-15'
---
```

Or move completed tasks to a dedicated section in the file:

```markdown
## Completed Items

- [x] Initial repository setup (2025-12-01)
- [x] Core doctype implementations (2025-12-15)
- [x] Basic custom script functionality (2025-12-20)
```

## Maintenance

- Review and update TODO files during sprint planning
- Move completed tasks to `docs/todo/archive/` (monthly or quarterly)
- Remove or update outdated tasks
- Ensure all active tasks have clear owners or assignees
- Update linked documentation when tasks are completed
