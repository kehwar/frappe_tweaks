# Plan: Integrate AC Rules with Workflow Actions

## Goal

Extend the AC Rules system to control workflow transitions dynamically, enabling complex permission logic (territory-based approvals, conditional validations) without creating multiple workflow transitions or roles.

## Background

### Current Workflow System

1. Workflow configured with actions and transitions
2. Roles assigned to transitions determine who can perform them
3. Conditions (safe Python) can conditionally enable transitions

### Problem

- **Multiple conditions require multiple transitions**: Each validation (min price, duplicates, etc.) needs separate transitions
- **Transition explosion**: The "safe" transition where all checks pass grows with each new condition
- **Territory-based approvals**: Need separate transitions and roles for each territory's manager
- **Visibility vs. Actions**: Cannot restrict actions without restricting read permissions

### Desired Solution

Use AC Rules to manage workflow action permissions:
- Workflow has actions/transitions but minimal conditions and "allow all roles"
- AC Resources define workflow actions (Submit, Request Approval, Approve, etc.)
- AC Rules with Query Filters control who can perform which actions
- Separate rules for different validation scenarios and territories

## Key Architectural Principles

### Name-Based Matching (No Explicit Linking)

**Workflow Action Master** (Frappe core):
- Doctype: `Workflow Action Master`
- Field: `workflow_action_name` (unique string)
- Created by users when defining workflows
- Examples: "Submit", "Approve", "Request Approval", "Reject"

**AC Action** (Tweaks module):
- Doctype: `AC Action`
- Field: `action` (unique string, primary key)
- Created manually by users
- Examples: "Read", "Write", "Submit", "Approve", "Request Approval"

**Matching Logic**:
- When checking permissions, compare `transition.action` (from Workflow) with `ac_action.action`
- If names match exactly, AC Rules apply
- If no matching AC Action exists, workflow action is unmanaged (fall back to workflow roles)
- User is responsible for keeping names consistent

**Benefits of This Approach**:
- ✅ Simple: No linking tables or sync mechanisms
- ✅ Flexible: Users can manage which workflow actions to control via AC Rules
- ✅ No coupling: AC Rules and Workflows remain independent systems
- ✅ Progressive adoption: Users can add AC Rule management for specific actions incrementally
- ✅ No data migration: Works with existing workflows

## Implementation Steps

### 1. Hook into existing before_transition event (No Frappe changes needed)

**Goal**: Use Frappe's existing document-level `before_transition` hook via doc_events.

**Approach**: Register a global handler for the `before_transition` event that runs for all doctypes.

**Why this works**:
- Frappe already calls `doc.run_method("before_transition", transition=transition)` before applying workflow
- Frappe's doc_events system allows hooking into this for all doctypes using `"*"`
- No monkey patching needed
- Zero changes to Frappe required

**Changes to tweaks/hooks.py**:

```python
# In tweaks/hooks.py

doc_events = {
    "*": {
        # ... existing hooks ...
        "before_transition": [
            "tweaks.utils.workflow.check_workflow_transition_permission"
        ],
    }
}
```

**Create new file tweaks/utils/workflow.py**:

```python
# In tweaks/utils/workflow.py

import frappe
from frappe import _

def check_workflow_transition_permission(doc, method=None, transition=None):
    """
    Doc event handler for before_transition.
    Checks AC Rules if the workflow action is managed.
    Raises exception to block transition if permission denied.
    
    Args:
        doc: Document being transitioned
        method: Method name (before_transition)
        transition: Transition object with action, state, next_state, etc.
    """
    if not transition:
        return
    
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access
    
    user = frappe.session.user
    
    # Check if AC Rules manage this workflow action
    result = has_resource_access(
        doctype=doc.doctype,
        action=transition.action,  # e.g., "Approve", "Submit"
        user=user
    )
    
    if not result.get("unmanaged"):
        # AC Rules are managing this workflow action
        if not result.get("access"):
            frappe.throw(
                _("You do not have permission to perform this workflow action"),
                frappe.PermissionError
            )
    
    # If unmanaged or has access, do nothing (let transition proceed)
```

**Files to create/modify**:
- `tweaks/hooks.py` - Add before_transition to doc_events
- `tweaks/utils/workflow.py` - Create new file with handler function

**Rationale**:
- **Zero changes to Frappe** - Uses existing doc_events system
- **No monkey patching** - Clean hook registration
- **Global coverage** - Automatically applies to all workflow-enabled doctypes
- **Follows Frappe patterns** - Standard way to hook into document events
- **Clean and maintainable** - Easy to understand and debug

### 2. Add hook to filter workflow transitions (Frappe repo - minimal addition)

**Goal**: Add a single hook to Frappe's `get_transitions()` to allow filtering of available transitions.

**Why needed**: The `before_transition` event only runs when a transition is applied. We also need to filter which transitions are shown in the UI before the user clicks.

**Changes to frappe/model/workflow.py**:

```python
# In frappe/model/workflow.py, at the end of get_transitions() function
@frappe.whitelist()
def get_transitions(doc, workflow=None, raise_exception=False):
    """Return list of possible transitions for the given doc"""
    # ... existing code to get transitions ...
    
    # NEW HOOK: Allow custom filtering of transitions (ADD THIS)
    for method in frappe.get_hooks("filter_workflow_transitions", []):
        transitions = frappe.call(method, doc=doc, transitions=transitions, workflow=workflow) or transitions
    
    return transitions
```

**Changes to frappe/hooks.py**:
```python
# Add hook definition
filter_workflow_transitions = []
```

**Files to modify**:
- `frappe/model/workflow.py` - Add hook call (2 lines)
- `frappe/hooks.py` - Define hook name (1 line)

**Total Frappe changes**: 3 lines of code

**Rationale**:
- Minimal, focused change to Frappe
- Generic hook that any module can use
- Follows existing Frappe hook patterns
- No knowledge of AC Rules or tweaks

### 3. Implement transition filtering in Tweaks (Tweaks repo)

**Goal**: Register handler for the `filter_workflow_transitions` hook to filter UI transitions.

**Changes to tweaks/hooks.py**:

```python
# In tweaks/hooks.py

# Add to existing doc_events
doc_events = {
    "*": {
        # ... existing hooks ...
        "before_transition": [
            "tweaks.utils.workflow.check_workflow_transition_permission"
        ],
    }
}

# Add new hook for filtering transitions
filter_workflow_transitions = [
    "tweaks.utils.workflow.filter_transitions_by_ac_rules"
]
```

**Add to tweaks/utils/workflow.py**:

```python
# In tweaks/utils/workflow.py

def filter_transitions_by_ac_rules(doc, transitions, workflow):
    """
    Hook handler for filter_workflow_transitions.
    Filters out transitions the user doesn't have permission for via AC Rules.
    
    Args:
        doc: Document object
        transitions: List of transition objects
        workflow: Workflow object
        
    Returns:
        Filtered list of transitions
    """
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access
    
    user = frappe.session.user
    filtered_transitions = []
    
    for transition in transitions:
        # Check if AC Rules manage this workflow action
        result = has_resource_access(
            doctype=doc.doctype,
            action=transition.action,
            user=user
        )
        
        if not result.get("unmanaged"):
            # Managed by AC Rules - check permission
            if result.get("access"):
                filtered_transitions.append(transition)
            # If no access, skip this transition
        else:
            # Unmanaged by AC Rules - include it
            filtered_transitions.append(transition)
    
    return filtered_transitions
```

**Files to create/modify**:
- `tweaks/hooks.py` - Register filter hook
- `tweaks/utils/workflow.py` - Add filter function

**Rationale**:
- Filters transitions before showing in UI
- User only sees workflow buttons they have permission to use
- Consistent with permission check in `before_transition`

---

### 4. Integrate with Workflow Action doctype notifications (Tweaks repo)

**Goal**: Filter Workflow Action notifications based on AC Rules so users only see workflow actions they have permission to perform.

**How it works**: Frappe already has a `permission_query_conditions` hook system. In `frappe/hooks.py`:
```python
permission_query_conditions = {
    "Workflow Action": "frappe.workflow.doctype.workflow_action.workflow_action.get_permission_query_conditions",
    # ... other doctypes
}
```

We can **override this hook** in tweaks to add AC Rules checking.

**Files to modify**:
- `tweaks/hooks.py` - Override permission_query_conditions for Workflow Action
- `tweaks/utils/workflow.py` - Add permission query function

**Implementation**:

### A. Add hook in tweaks/hooks.py

```python
# In tweaks/hooks.py

permission_query_conditions = {
    "*": [
        # ... existing handlers ...
        "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_permission_query_conditions"
    ],
    # Add AC Rules filtering to Workflow Action (additive - combines with Frappe's logic)
    "Workflow Action": [
        "tweaks.utils.workflow.get_workflow_action_permission_query_conditions"
    ]
}
```

### B. Add function in tweaks/utils/workflow.py

```python
def get_workflow_action_permission_query_conditions(user=None, doctype=None):
    """
    Additional permission query conditions for Workflow Action doctype.
    
    Adds AC Rules filtering on top of Frappe's role-based filtering.
    Frappe automatically combines this with the original conditions using AND.
    
    Strategy:
    1. Get all (doctype, state, action) triples from open workflow actions
    2. For each (doctype, action), get AC Rules filter as SELECT query
    3. Group by (doctype, state) and OR all action queries together
    4. Build final condition checking if reference_name is in any allowed action query
    
    Args:
        user: User to check (defaults to session user)
        doctype: DocType name (should be "Workflow Action")
    
    Returns:
        str: SQL WHERE clause for AC Rules filtering, or "" if no filtering needed
    """
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query
    
    if not user:
        user = frappe.session.user
    
    if user == "Administrator":
        return ""
    
    # Get all distinct (reference_doctype, workflow_state, action) triples
    doctype_state_action_triples = frappe.db.sql("""
        SELECT DISTINCT 
            wa.reference_doctype,
            wa.workflow_state,
            wt.action
        FROM `tabWorkflow Action` wa
        INNER JOIN `tabWorkflow` w 
            ON w.document_type = wa.reference_doctype
        INNER JOIN `tabWorkflow Transition` wt
            ON wt.parent = w.name 
            AND wt.state = wa.workflow_state
        WHERE wa.status = 'Open'
    """, as_dict=True)
    
    if not doctype_state_action_triples:
        return ""
    
    # Group triples by (doctype, state)
    # Structure: {(doctype, state): [action1, action2, ...]}
    grouped = {}
    for triple in doctype_state_action_triples:
        key = (triple.reference_doctype, triple.workflow_state)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(triple.action)
    
    # Build conditions for each (doctype, state) group
    conditions = []
    
    for (reference_doctype, workflow_state), actions in grouped.items():
        # Get AC Rules filter for each action
        action_queries = []
        has_total_access = False  # Track if any action has unmanaged or total access
        
        for action in actions:
            action_scrubbed = frappe.scrub(action)
            
            # Get filter query from AC Rules
            result = get_resource_filter_query(
                doctype=reference_doctype,
                action=action_scrubbed,
                user=user,
                debug=False
            )
            
            if result.get("unmanaged") or result.get("access") == "total":
                # Not managed by AC Rules OR user has total access
                # Either way, AC Rules doesn't restrict this doctype/state
                # No need to add any conditions for this doctype/state
                has_total_access = True
                break  # Short-circuit: no need to check other actions
            elif result.get("access") == "none":
                # User has no access for this action via AC Rules
                # Don't add query (implicitly blocks this action)
                pass
            elif result.get("access") == "partial":
                # User has conditional access
                filter_query = result.get("query", "")
                if filter_query:
                    # Build SELECT query that returns allowed document names
                    select_query = f"""
                        SELECT name 
                        FROM `tab{reference_doctype}` 
                        WHERE {filter_query}
                    """
                    action_queries.append(f"`tabWorkflow Action`.`reference_name` IN ({select_query})")
        
        # If any action has total access, skip this doctype/state (no AC Rules restrictions)
        if has_total_access:
            continue
        
        # If no action queries, all actions must have access=none (all blocked by AC Rules)
        if not action_queries:
            # Block workflow actions for this doctype/state entirely
            conditions.append(f"""
                NOT (
                    `tabWorkflow Action`.`reference_doctype` = {frappe.db.escape(reference_doctype)}
                    AND `tabWorkflow Action`.`workflow_state` = {frappe.db.escape(workflow_state)}
                )
            """)
        else:
            # Combine action queries with OR
            # Show workflow action if it's this doctype/state AND reference_name matches at least one allowed action
            combined_action_queries = " OR ".join([f"({q})" for q in action_queries])
            conditions.append(f"""
                (
                    `tabWorkflow Action`.`reference_doctype` = {frappe.db.escape(reference_doctype)}
                    AND `tabWorkflow Action`.`workflow_state` = {frappe.db.escape(workflow_state)}
                    AND ({combined_action_queries})
                )
            """)
    
    if not conditions:
        return ""
    
    # Combine all conditions with OR (each condition handles a different doctype/state)
    return " OR ".join([f"({c})" for c in conditions])
```

**How it works**:

1. **Get all triples**: Single query joins Workflow Action → Workflow → Workflow Transition to get (doctype, state, action) combinations

2. **Group by (doctype, state)**: Multiple actions can transition from the same state, so we group them together

3. **Get AC Rules filter per action**: For each action:
   - **Unmanaged or Total access**: Set `has_total_access = True` and break (no AC Rules restrictions apply)
   - **None access**: Don't add query (blocks this action)
   - **Partial access**: Add `SELECT name FROM tab{doctype} WHERE {filter}` to action queries

4. **Optimization**: If `has_total_access` is set, skip this (doctype, state) entirely - no AC Rules conditions needed

5. **Build conditions**: For each (doctype, state) without total access:
   - **If no action queries**: All actions blocked, add condition to hide all workflow actions for this doctype/state
   - **If action queries exist**: Combine with OR, show workflow action only if `(doctype = X AND state = Y AND (query1 OR query2 OR ...))`

6. **Combine final conditions**: Use OR to combine all (doctype, state) conditions - workflow action shown if it matches ANY condition

**Example SQL output**:

**Scenario 1**: User has partial access to "Approve" (grand_total >= 10000) and total access to "Reject":
```sql
-- No condition added for Quotation/Pending (has_total_access = True due to Reject)
-- Frappe's role-based filtering handles it
```

**Scenario 2**: User has partial access to "Approve" (grand_total >= 10000) and no access to "Reject":
```sql
(
    `tabWorkflow Action`.`reference_doctype` = 'Quotation'
    AND `tabWorkflow Action`.`workflow_state` = 'Pending'
    AND (
        `tabWorkflow Action`.`reference_name` IN (
            SELECT name FROM `tabQuotation` WHERE `tabQuotation`.`grand_total` >= 10000
        )
    )
)
```

**Scenario 3**: User has no access to any actions for Quotation/Pending:
```sql
NOT (
    `tabWorkflow Action`.`reference_doctype` = 'Quotation'
    AND `tabWorkflow Action`.`workflow_state` = 'Pending'
)
```

**Multiple doctype/state combinations** are combined with OR:
```sql
(
    (doctype1 condition)
    OR (doctype2 condition)
    OR NOT (blocked doctype3)
)
```

---

## Workflow Action Email Notifications

### How Email Notifications Currently Work

When a document's workflow state changes, Frappe sends email notifications to users who can take action:

1. **`process_workflow_actions(doc, state)`** is called after workflow state changes
2. Gets **next possible transitions** from the new state
3. For each transition, gets **users with the allowed role**
4. **Filters users** by:
   - `has_approval_access(user, doc, transition)` - checks allow_self_approval
   - `user_has_permission(user)` - checks `has_permission(doctype=doc, user=user)` with **ptype="read"**
5. For each filtered user, builds a list of **possible actions** they can take
6. Sends **one email per user** with buttons for all their possible actions

**Key function**: `get_users_next_action_data(transitions, doc)`
```python
for transition in transitions:
    users = get_users_with_role(transition.allowed)
    filtered_users = [
        user for user in users 
        if has_approval_access(user, doc, transition) 
        and user_has_permission(user)  # Checks READ permission only!
    ]
    # Build action list per user
```

**Email contains**: Buttons for each action the user can perform (e.g., "Approve", "Reject")

### The Problem with AC Rules Integration

**Current `user_has_permission` check is insufficient!**

`has_permission(doctype=doc, user=user)` uses default `ptype="read"`, which checks:
- ✅ Does user have READ permission on the document?

But AC Rules are action-specific:
- `doctype="Quotation"`, `action="approve"` - Min price $10,000
- `doctype="Quotation"`, `action="reject"` - No restrictions

**Result**: A user might get an "Approve" button in the email even if they don't have AC Rules access to "approve" this specific document!

### Solution: Add Hook to Filter Users by Action

We need to add a hook in Frappe that allows external apps (like tweaks) to filter users based on the specific action.

#### A. Add Hook to Frappe

**File**: `frappe/hooks.py`
```python
# Add hook definition
filter_workflow_action_users = []
```

**File**: `frappe/workflow/doctype/workflow_action/workflow_action.py`

Modify `get_users_next_action_data`:
```python
def get_users_next_action_data(transitions, doc):
    user_data_map = {}

    @frappe.request_cache
    def user_has_permission(user: str) -> bool:
        from frappe.permissions import has_permission
        return has_permission(doctype=doc, user=user)

    for transition in transitions:
        users = get_users_with_role(transition.allowed)
        filtered_users = [
            user for user in users 
            if has_approval_access(user, doc, transition) 
            and user_has_permission(user)
        ]
        
        # NEW: Apply external filters
        for method in frappe.get_hooks("filter_workflow_action_users", []):
            filtered_users = frappe.call(method, users=filtered_users, transition=transition, doc=doc) or filtered_users
        
        if doc.get("owner") in filtered_users and not transition.get("send_email_to_creator"):
            filtered_users.remove(doc.get("owner"))
        
        # ... rest of logic (build user_data_map)
    
    return user_data_map
```

#### B. Implement Hook in Tweaks

**File**: `tweaks/hooks.py`
```python
filter_workflow_action_users = [
    "tweaks.utils.workflow.filter_workflow_action_users_by_ac_rules"
]
```

**File**: `tweaks/utils/workflow.py`
```python
def filter_workflow_action_users_by_ac_rules(users, transition, doc):
    """
    Filter users by AC Rules for the specific workflow action.
    
    Args:
        users: List of user IDs already filtered by role and read permission
        transition: Workflow transition dict with 'action', 'allowed', etc.
        doc: Document being actioned
    
    Returns:
        List of user IDs that have AC Rules access to perform this action
    """
    if not users:
        return users
    
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access
    
    action = transition.get("action")
    if not action:
        return users
    
    action_scrubbed = frappe.scrub(action)
    filtered = []
    
    for user in users:
        # Check if user has AC Rules access to this action
        result = has_resource_access(
            doctype=doc.doctype,
            action=action_scrubbed,
            user=user
        )
        
        if result.get("unmanaged"):
            # Not managed by AC Rules, user already passed role check
            filtered.append(user)
        elif result.get("access"):
            # User has AC Rules access to this action
            filtered.append(user)
        # If access == False, don't add user
    
    return filtered
```

**Rationale**:
- Hook in Frappe keeps it generic and extensible
- Tweaks implements action-specific filtering
- Users only get email if they have AC Rules access to the specific action
- Maintains separation: Frappe has no knowledge of tweaks/AC Rules

---

## Repository Changes Summary

### Frappe Repository (Minimal Changes)

**Files Modified**:
1. `frappe/model/workflow.py` - Add 1 hook call to `get_transitions()` (2 lines)
2. `frappe/hooks.py` - Define 2 hook names (2 lines)
3. `frappe/workflow/doctype/workflow_action/workflow_action.py` - Add hook call to filter users for email (2 lines)

**Total**: 6 lines of code

**Hook 1**: `filter_workflow_transitions`
- Called in `get_transitions()` to filter available transitions in UI
- Signature: `method(doc, transitions, workflow) -> filtered_transitions`

**Hook 2**: `filter_workflow_action_users` 
- Called in `get_users_next_action_data()` to filter users for email notifications
- Signature: `method(users, transition, doc) -> filtered_users`

**Nature of Changes**:
- Two generic hooks following Frappe patterns
- No knowledge of AC Rules or tweaks module
- Non-breaking, backward compatible
- Easy to review and merge

### Tweaks Repository (Main Implementation)

**Files Created/Modified**:
1. `tweaks/utils/workflow.py` - Create new file with handler functions (~100 lines including Step 3)
2. `tweaks/hooks.py` - Register handlers (~10 lines)

**Files Deprecated/To Remove**:
- `tweaks/custom/doctype/workflow.py` - Old implementation with monkey patches (remove after new implementation works)

**Total**: ~80-100 lines of new code

**Nature of Changes**:
- All AC Rules logic stays in tweaks
- Uses standard Frappe doc_events and hooks
- Clean utility module instead of monkey patches
- No coupling between frappe and tweaks

## User Workflow for Setup

### Step 1: Create Workflow (Standard Frappe)

1. Go to Workflow list
2. Create new Workflow for Quotation
3. Define workflow states (Draft, Pending Approval, Approved)
4. Define workflow transitions:
   - Action: "Submit", From: Draft, To: Pending Approval, Allowed Role: All
   - Action: "Approve", From: Pending Approval, To: Approved, Allowed Role: All
   - Action: "Reject", From: Pending Approval, To: Draft, Allowed Role: All

**Key Point**: Set "Allowed Role" to "All" or a very permissive role, since AC Rules will handle the actual permissions.

### Step 2: Create Workflow Action Master (Standard Frappe)

The workflow actions (Submit, Approve, Reject) are automatically available via Workflow Action Master.

**No manual step needed** - Frappe handles this automatically.

### Step 3: Create AC Actions (Tweaks - Manual)

1. Go to AC Action list
2. For each workflow action you want to manage with AC Rules, create an AC Action:
   - Action: "Submit"
   - Action: "Approve"
   - Action: "Reject"

**Naming is critical**: The AC Action name must exactly match the Workflow Action name.

### Step 4: Create AC Resource (Tweaks)

1. Go to AC Resource list
2. Create resource for Quotation
3. Set Type: DocType
4. Set DocType: Quotation
5. Set Managed Actions: Select
6. Add the workflow actions you want to manage:
   - Submit
   - Approve
   - Reject

### Step 5: Create Query Filters (Tweaks)

1. Go to Query Filter list
2. Create principal filters (WHO can perform actions):
   ```
   Name: Sales Managers
   Reference DocType: Role
   Filter Type: JSON
   Filters: [["name", "=", "Sales Manager"]]
   ```

3. Create resource filters (WHICH records):
   ```
   Name: Below Min Price
   Reference DocType: Quotation
   Filter Type: Python
   Filters:
   min_price = 1000
   conditions = f"`tabQuotation`.`grand_total` < {min_price}"
   ```

### Step 6: Create AC Rules (Tweaks)

1. **Rule: Forbid Submit if Below Min Price**
   - Title: "Forbid Submit if Below Min Price"
   - Type: Forbid
   - Resource: Quotation Resource
   - Actions: Submit
   - Principals: All (no filter = everyone)
   - Resources: Below Min Price

2. **Rule: Allow Approve for Sales Managers**
   - Title: "Sales Managers Can Approve"
   - Type: Permit
   - Resource: Quotation Resource
   - Actions: Approve
   - Principals: Sales Managers
   - Resources: (empty = all records)

### Step 7: Test

1. Create a quotation under $1000
2. Try to Submit → Should be blocked (Forbid rule)
3. Try to Approve as non-manager → Should be blocked (no Permit rule)
4. Try to Approve as Sales Manager → Should work (Permit rule)

## Design Decisions

### 1. Name Matching Strategy

**Decision**: Use exact string matching between Workflow Action and AC Action names.

**Rationale**:
- Simple and transparent
- No hidden magic or auto-sync
- User has full control
- Easy to understand and debug
- Follows principle of explicit configuration

**User Responsibility**:
- Create AC Actions with same names as Workflow Actions
- Keep names synchronized manually
- System will warn if AC Action doesn't exist (unmanaged = falls back to workflow roles)

### 2. No Doctype Prefix

**Decision**: Do not prefix workflow action names with doctype (use "Approve", not "Quotation:Approve").

**Rationale**:
- Simpler naming convention
- Action names are already scoped by AC Resource's doctype
- Same action name ("Approve") can be used across multiple doctypes with different rules
- Easier for users to understand and configure

### 3. AC Rules vs. Workflow Roles Precedence

**Decision**: AC Rules take precedence when resource exists and manages the action.

**Logic**:
```
if AC Action exists with this name:
    if AC Resource manages this action for this doctype:
        Use AC Rules only (unmanaged = false)
        Check permit/forbid rules
    else:
        AC Action exists but not managed for this doctype (unmanaged = true)
        Fall back to workflow roles
else:
    No AC Action with this name (unmanaged = true)
    Fall back to workflow roles
```

**Rationale**:
- Clean separation: Either AC Rules control it, or workflow roles control it
- Predictable behavior: Users know which system is in control
- Progressive adoption: Add AC Rule management per action, not all-or-nothing

### 4. No Auto-Sync or Linking

**Decision**: No automatic synchronization or linking between Workflow Action Master and AC Action.

**Rationale**:
- User explicitly controls which workflow actions are managed by AC Rules
- No hidden coupling between systems
- Simpler code - no sync jobs or triggers
- Clear mental model: If AC Action exists, it can be managed; if not, it's unmanaged
- Progressive adoption: Add AC Rule management incrementally

**Trade-off**: User must manually create AC Actions for workflow actions they want to manage. This is acceptable because:
- It's a one-time setup per action name
- Action names are reusable across doctypes
- Explicit is better than implicit
- Easy to document and teach

### 5. Workflow Action Doctype Integration

**Decision**: Optional/Low priority - can be deferred to later phase.

**Rationale**:
- Core workflow permission checks work without this
- Workflow Action notifications are supplementary
- Can be added incrementally after core implementation is stable

### 6. Performance Considerations

**Decision**: Accept overhead, leverage existing AC Rules caching.

**Rationale**:
- AC Rules already have request-level caching via `@frappe.request_cache`
- Rule map is cached at site level
- Additional overhead per transition check should be minimal (< 10ms)
- Simpler implementation than custom caching
- Can optimize later if needed

### 7. UI Indicators for Forbidden Transitions

**Decision**: Generic "No Permission" message for users, detailed info in debug mode for System Managers.

**Rationale**:
- Consistent with existing Frappe permission messages
- Simple and secure
- Doesn't expose internal rule logic
- Debug mode available for troubleshooting

## Example Usage

### Scenario: Quotation with Min Price Check

**Step 1: Setup Workflow**
1. Create Workflow for Quotation
2. States: Draft → Pending Approval → Approved
3. Transitions:
   - "Submit": Draft → Pending Approval (Role: All)
   - "Request Approval": Draft → Pending Approval (Role: All)
   - "Approve": Pending Approval → Approved (Role: All)

**Step 2: Create AC Actions**
1. Create AC Action: "Submit"
2. Create AC Action: "Request Approval"  
3. Create AC Action: "Approve"

**Step 3: Create AC Resource**
1. Name: "Quotation Resource"
2. Type: DocType
3. DocType: Quotation
4. Managed Actions: Select
5. Actions: Submit, Request Approval, Approve

**Step 4: Create Query Filters**
1. **Filter**: "Below Min Price"
   - Reference DocType: Quotation
   - Filter Type: Python
   ```python
   min_price = 1000
   conditions = f"`tabQuotation`.`grand_total` < {min_price}"
   ```

**Step 5: Create AC Rules**
1. **Rule**: "Forbid Submit if Below Min Price"
   - Type: Forbid
   - Resource: Quotation Resource
   - Actions: Submit
   - Principals: (empty = all users)
   - Resources: Below Min Price

2. **Rule**: "Allow Request Approval if Below Min Price"
   - Type: Permit
   - Resource: Quotation Resource
   - Actions: Request Approval
   - Principals: Sales User (role filter)
   - Resources: Below Min Price

3. **Rule**: "Allow Approve for Sales Managers"
   - Type: Permit
   - Resource: Quotation Resource
   - Actions: Approve
   - Principals: Sales Manager (role filter)
   - Resources: (empty = all records)

**Result**:
- Quotations under $1000 cannot use "Submit" transition
- Users can use "Request Approval" transition instead
- Sales Managers can use "Approve" transition on any quotation

### Scenario: Territory-based Approval

**Setup**:

1. **Query Filters**:
   - "North Territory Sales Managers"
     - Reference DocType: User  
     - Filter: `[["territory", "=", "North"]]`
   - "South Territory Sales Managers"
     - Reference DocType: User
     - Filter: `[["territory", "=", "South"]]`
   - "North Territory Quotations"
     - Reference DocType: Quotation
     - Filter: `[["territory", "=", "North"]]`
   - "South Territory Quotations"
     - Reference DocType: Quotation
     - Filter: `[["territory", "=", "South"]]`

2. **AC Actions**:
   - Create AC Action: "Approve"

3. **AC Resource**:
   - Type: DocType, DocType: Quotation
   - Managed Actions: Approve

4. **AC Rules**:
   
   **Rule 1**: "North Territory Approval"
   - Type: Permit
   - Resource: Quotation Resource
   - Actions: Approve
   - Principals: North Territory Sales Managers
   - Resources: North Territory Quotations
   
   **Rule 2**: "South Territory Approval"
   - Type: Permit
   - Resource: Quotation Resource
   - Actions: Approve
   - Principals: South Territory Sales Managers
   - Resources: South Territory Quotations

**Result**:
- North managers can only approve North quotations
- South managers can only approve South quotations
- No need for separate workflow transitions
- No need for separate roles per territory

## Migration Plan

### Phase 1: Core Implementation (Week 1)

**Frappe Repository**:
- [ ] Add `filter_workflow_transitions` hook to `frappe/model/workflow.py` in `get_transitions()`
- [ ] Add `filter_workflow_action_users` hook to `frappe/workflow/doctype/workflow_action/workflow_action.py` in `get_users_next_action_data()`
- [ ] Define both hooks in `frappe/hooks.py`
- [ ] Create PR for frappe repository

**Tweaks Repository**:
- [ ] Create new file `tweaks/utils/workflow.py`
- [ ] Implement `check_workflow_transition_permission()` in `tweaks/utils/workflow.py`
- [ ] Implement `filter_transitions_by_ac_rules()` in `tweaks/utils/workflow.py`
- [ ] Implement `get_workflow_action_permission_query_conditions()` in `tweaks/utils/workflow.py`
- [ ] Implement `filter_workflow_action_users_by_ac_rules()` in `tweaks/utils/workflow.py`
- [ ] Add `before_transition` handler to doc_events in `tweaks/hooks.py`
- [ ] Register `filter_workflow_transitions` hook in `tweaks/hooks.py`
- [ ] Register `permission_query_conditions` for Workflow Action in `tweaks/hooks.py`
- [ ] Register `filter_workflow_action_users` hook in `tweaks/hooks.py`
- [ ] Remove deprecated `tweaks/custom/doctype/workflow.py`

### Phase 2: Documentation and Examples (Week 2)
- [ ] Update AC Rules instruction file
- [ ] Create setup guide for users
- [ ] Create example: Min price check
- [ ] Create example: Territory-based approval
- [ ] Add troubleshooting guide

### Phase 3: Optional Enhancements (Week 3+)
- [ ] Add `workflow_action_permission_query_conditions` hook to frappe (if needed)
- [ ] Workflow Action doctype integration in tweaks
- [ ] UI helper for creating AC Actions from workflow
- [ ] Bulk AC Action creation utility
- [ ] Advanced debugging tools

### Phase 4: Rollout
- [ ] Review and merge frappe PR
- [ ] Deploy to staging
- [ ] Train key users
- [ ] Monitor performance
- [ ] Deploy to production
- [ ] Gather feedback
- [ ] Iterate based on feedback

## Frappe Hooks Design

### Existing Hook: `before_transition` (doc_events)

**Already exists in Frappe** - No changes needed.

**How it works**:
- Document-level method hook
- Called via `doc.run_method("before_transition", transition=transition)`
- Can be hooked globally via doc_events in any app

**Usage in tweaks/hooks.py**:
```python
doc_events = {
    "*": {
        "before_transition": ["tweaks.custom.doctype.workflow.check_workflow_transition_permission"]
    }
}
```

**Parameters**:
- `doc` - Document object
- `method` - Method name ("before_transition")
- `transition` - Transition object being applied

**Expected Behavior**:
- Hook can raise exception to block transition
- Hook should not modify doc state
- Multiple hooks are called in order

**Example Use Cases**:
- Custom permission checks (AC Rules) ✅
- Audit logging
- External system validation
- Custom business rules

### New Hook: `filter_workflow_transitions` (New - 3 lines in Frappe)

**Purpose**: Allow modules to filter the list of available transitions before showing to user.

**When Called**: In `get_transitions()`, after all transitions are collected.

**Parameters**:
- `doc` - Document object
- `transitions` - List of transition objects
- `workflow` - Workflow object

**Expected Return**: Filtered list of transitions (or None to keep original list)

**Expected Behavior**:
- Hook receives full list of transitions
- Hook returns filtered list (or None)
- Multiple hooks are called in sequence, each receiving output of previous hook
- Final filtered list is returned to caller

**Example Use Cases**:
- Permission-based filtering (AC Rules) ✅
- Context-based filtering
- Dynamic transition availability
- Custom business logic

### New Hook: `filter_workflow_action_users` (New - 2 lines in Frappe)

**Purpose**: Allow modules to filter the list of users who receive workflow action email notifications.

**When Called**: In `get_users_next_action_data()`, after users are filtered by role and read permission.

**Parameters**:
- `users` - List of user IDs already filtered by role
- `transition` - Transition object being processed
- `doc` - Document object

**Expected Return**: Filtered list of user IDs (or None to keep original list)

**Expected Behavior**:
- Hook receives list of users who have the role and read permission
- Hook returns filtered list based on action-specific logic
- Multiple hooks are called in sequence, each receiving output of previous hook
- Final filtered list is used for email notifications

**Example Use Cases**:
- Action-specific permission filtering (AC Rules) ✅
- Custom notification rules
- External system checks
- Advanced approval workflows

## Open Questions

1. Should workflow action names include doctype prefix?
   - **Resolved**: No prefix needed, action names scoped by AC Resource's doctype

2. Should we auto-sync AC Actions from Workflow Actions?
   - **Resolved**: No auto-sync, user creates AC Actions manually for explicit control

3. Should we add a UI button on Workflow to "Create AC Actions"?
   - **Recommendation**: No, user creates AC Actions manually for explicit control

4. How do we handle action name changes in Workflow?
   - **Recommendation**: User must update AC Action name manually (rare occurrence)

5. Should we show warning if Workflow Action has no matching AC Action?
   - **Recommendation**: No warning needed - unmanaged is valid state

6. Should we support regex or pattern matching for action names?
   - **Recommendation**: No - exact string matching only, keeps it simple

## Success Criteria

1. ✅ Can control workflow transitions using AC Rules with name-based matching
2. ✅ Can use Query Filters for conditional workflow permissions
3. ✅ Can assign territory-based approvers without multiple roles or transitions
4. ✅ Workflow UI correctly shows/hides buttons based on AC Rules
5. ✅ Backward compatible - existing workflows work without changes
6. ✅ Clear user documentation with step-by-step setup
7. ✅ User can progressively adopt AC Rules per action
8. ✅ Unmanaged actions fall back to workflow roles seamlessly
9. ✅ System is simple enough to explain in 5 minutes
