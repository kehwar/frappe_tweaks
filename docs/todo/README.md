# Frappe Tweaks - TODO and Implementation Tracking

This folder contains documentation for tracking current and future implementations, tasks, and improvements for the frappe_tweaks project.

## Purpose

The `docs/todo/` directory serves as the central location for:
- Tracking ongoing development tasks
- Planning future feature implementations
- Documenting technical debt and improvements
- Managing project roadmap items

## Active TODO Items

### High Priority

#### 1. Test Infrastructure Overhaul
**Status**: In Progress (2025-12-31)  
**Priority**: High  
**Description**: Clean up and recreate test files with proper CI/CD integration

**Tasks**:
- [x] Delete all current test files in the repository (2025-12-31)
  - Location: `tweaks/tweaks/doctype/*/test_*.py`
  - Location: `tweaks/tweaks/sync_job_type/*/test_*.py`
  - Reason: Test files will be recreated with improved structure and coverage
  
- [x] Implement GitHub Actions CI workflow (2025-12-31)
  - [x] Create `.github/workflows/tests.yml` for automated testing
  - [x] Configure test environment with Frappe bench setup
  - [x] Add test job for Python unit tests
  - [x] Add linting job (ruff, black, isort)
  - [x] Configure test coverage reporting (codecov integration)
  - [x] Add status badge to README.md
  
- [ ] Recreate test files with improved structure
  - [ ] Follow Frappe test framework best practices
  - [ ] Ensure proper test isolation
  - [ ] Add comprehensive test coverage for core features
  - [ ] Document testing conventions in main instructions

**Test Files to be Deleted** (20 files total):
```
./tweaks/tweaks/doctype/ac_settings/test_ac_settings.py
./tweaks/tweaks/doctype/event_script/test_event_script.py
./tweaks/tweaks/doctype/ac_principal/test_ac_principal.py
./tweaks/tweaks/doctype/business_logic_link_action/test_business_logic_link_action.py
./tweaks/tweaks/doctype/ac_rule/test_ac_rule.py
./tweaks/tweaks/doctype/open_observe_api/test_open_observe_api.py
./tweaks/tweaks/doctype/peru_api_com_log/test_peru_api_com_log.py
./tweaks/tweaks/doctype/sync_job_type/test_sync_job_type.py
./tweaks/tweaks/doctype/business_logic/test_business_logic.py
./tweaks/tweaks/doctype/peru_api_com/test_peru_api_com.py
./tweaks/tweaks/doctype/query_filter/test_query_filter.py
./tweaks/tweaks/doctype/sunat_tipo_documento_identidad/test_sunat_tipo_documento_identidad.py
./tweaks/tweaks/doctype/peru_api_com_console/test_peru_api_com_console.py
./tweaks/tweaks/doctype/doctype_group/test_doctype_group.py
./tweaks/tweaks/doctype/ac_action/test_ac_action.py
./tweaks/tweaks/doctype/ac_rule_principal/test_ac_rule_principal.py
./tweaks/tweaks/doctype/ac_resource/test_ac_resource.py
./tweaks/tweaks/doctype/sync_job/test_sync_job.py
./tweaks/tweaks/doctype/business_logic_category/test_business_logic_category.py
./tweaks/tweaks/sync_job_type/test_hooks_sync/test_hooks_sync.py
```

### Medium Priority

#### 2. Documentation Improvements
**Status**: In Progress  
**Priority**: Medium  

**Tasks**:
- [x] Create `docs/todo/` folder structure
- [x] Create main instructions file (this file)
- [ ] Add documentation for each major feature
- [ ] Create developer setup guide
- [ ] Add API documentation
- [ ] Document deployment procedures

#### 3. Code Quality Improvements
**Status**: Planned  
**Priority**: Medium  

**Tasks**:
- [ ] Add pre-commit hooks for code formatting
- [ ] Configure Black or similar formatter for Python
- [ ] Add ESLint configuration for JavaScript
- [ ] Implement code review checklist
- [ ] Add CONTRIBUTING.md guidelines

### Low Priority

#### 4. Feature Enhancements
**Status**: Backlog  
**Priority**: Low  

**Tasks**:
- [ ] Review and update Event Scripts (marked for deprecation)
- [ ] Improve error handling and logging
- [ ] Add more comprehensive examples in documentation
- [ ] Performance optimization review

## Completed Items

- [x] Initial repository setup
- [x] Core doctype implementations
- [x] Basic custom script functionality

## Notes

- This file should be updated regularly as tasks progress
- Each major feature should have its own detailed TODO file if needed
- Use this as a reference for sprint planning and prioritization
- Link related GitHub issues and pull requests where applicable

## Related Documentation

- Main Instructions: `.github/copilot-instructions.md`
- Sync Job Framework: `.github/instructions/sync-job.instructions.md`
- OpenObserve API: `.github/instructions/open-observe-api.instructions.md`
- Instructions Guidelines: `.github/instructions/instructions.instructions.md`

## Conventions

- Use `[ ]` for pending tasks
- Use `[x]` for completed tasks
- Add dates when marking tasks as completed
- Include relevant file paths and line numbers when applicable
- Keep descriptions clear and actionable
