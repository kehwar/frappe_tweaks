# Event Scripts Migration Report

## Overview

This report extracts all Event Scripts currently configured in the system to help with migration to Server Scripts or AC Rules. Event Scripts are deprecated and will be removed in future versions of Frappe Tweaks.

## Purpose

The report provides a comprehensive view of all Event Scripts, including:
- Configuration details (doctype, event, priority, etc.)
- User/role filtering information
- Script preview
- Parameter count
- **Recommended migration target** (Server Script or AC Rule)
- **Specific migration notes** for each script

## Usage

1. Navigate to: **Reports > Event Scripts Migration**
2. Apply filters as needed:
   - **Disabled**: Filter by enabled/disabled status
   - **Document Type**: Filter by specific DocType
   - **DocType Event**: Filter by specific event type
   - **Migration Target**: Filter by recommended migration path

3. Review the results and plan your migration strategy

## Migration Paths

### Server Scripts
Most Event Scripts should migrate to Server Scripts. This includes:
- Document lifecycle events (validate, before_save, on_update, etc.)
- Submission/cancellation events
- Delete events
- Custom validation logic
- Workflow events (when not permission-related)

**Migration Steps:**
1. Create a new Server Script in Frappe
2. Select the appropriate event type
3. Copy the script code
4. Reimplement any user/role filtering in the script logic
5. Test thoroughly
6. Disable the Event Script
7. Delete the Event Script after verification

### AC Rules
Permission-related Event Scripts should migrate to AC Rules. This includes:
- `has_permission` events
- `has_field_permission` events
- Access control logic

**Migration Steps:**
1. Create Query Filters for principals (who has access)
2. Create Query Filters for resources (what records they can access)
3. Create an AC Resource for the target DocType
4. Create AC Rules linking principals and resources
5. Test thoroughly with different users
6. Disable the Event Script
7. Delete the Event Script after verification

## Report Columns

| Column | Description |
|--------|-------------|
| ID | Event Script identifier (click to open) |
| Title | Human-readable name |
| Disabled | Whether the script is disabled |
| Priority | Execution priority |
| Document Type | Target DocType |
| DocType Group | Target DocType Group (if applicable) |
| DocType Event | Event that triggers the script |
| Action | Permission action (for has_permission events) |
| Workflow Action | Workflow action (for transition events) |
| User Filter | Summary of user/role filters |
| User | Specific user filter |
| User Group | User group filter |
| Role | Role filter |
| Role Profile | Role profile filter |
| Script Preview | First 100 characters of script |
| Parameters | Count of Event Script Parameters |
| Migration Target | Recommended migration path |
| Migration Notes | Specific guidance for migration |

## Color Coding

- **Red**: Disabled scripts
- **Green**: Server Script target
- **Blue**: AC Rule target
- **Orange**: Either Server Script or AC Rule (case-by-case basis)

## Important Notes

1. **User/Role Filtering**: Event Scripts support user, user group, role, and role profile filtering. When migrating to Server Scripts, this logic must be implemented in the script code. AC Rules provide built-in principal filtering.

2. **Parameters**: Event Script Parameters are a custom feature. When migrating, you'll need to reimplement parameter resolution in your new scripts.

3. **Testing**: Always test migrated scripts thoroughly before deleting the original Event Scripts. Keep Event Scripts disabled while testing the new implementation.

4. **Backup**: Export or backup Event Scripts before deletion for reference.

5. **Document Type Groups**: Event Scripts can apply to DocType Groups. When migrating, you may need to create multiple Server Scripts or AC Rules, one for each DocType in the group.

## Related Documentation

- [AC Rule Instructions](../../../.github/instructions/ac-rule.instructions.md)
- [Frappe Server Scripts Documentation](https://frappeframework.com/docs/user/en/desk/scripting/server-script)

## Support

For questions or issues with migration, please consult:
- Project maintainers
- Frappe documentation
- AC Rule system documentation in `.github/instructions/`
