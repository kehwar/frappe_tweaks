# AC Rule Permission Flow Diagrams

## List View Filtering Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ User opens DocType List View (e.g., Customer)                      │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frappe calls permission_query_conditions hook                       │
│ → get_permission_query_conditions("Customer", "user@example.com")  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Check if user is Administrator?                                     │
│   YES → Return "" (full access)                                     │
│   NO  → Continue                                                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Call get_resource_filter_query()                                    │
│   - doctype: "Customer"                                             │
│   - action: "read"                                                  │
│   - user: "user@example.com"                                        │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Get AC Rules for Customer + Read action                             │
│   - Check if resource is managed (has AC Resources/Rules)           │
│   - If unmanaged → Return "" (fall through to Frappe permissions)   │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Filter rules by user (Principal Filtering)                          │
│   - Check if user matches principal filters                         │
│   - Only keep rules where user matches principals                   │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Build SQL WHERE clause from resource filters                        │
│   Permit rules: (filter1 OR filter2)                                │
│   Forbid rules: NOT (filter3 OR filter4)                            │
│   Final: (Permits) AND NOT (Forbids)                                │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Return SQL WHERE clause                                             │
│ Example: "(`tabCustomer`.`account_manager` = 'user@example.com')"  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frappe appends filter to query                                      │
│ SELECT * FROM `tabCustomer`                                         │
│ WHERE (AC Rule filter) AND (other conditions)                       │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ User sees filtered list of records                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Single Document Permission Check Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ User accesses specific document (e.g., Customer "CUST-001")        │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frappe calls has_permission hook                                    │
│ → has_permission(doc, ptype="write", user="user@example.com")      │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Check if user is Administrator?                                     │
│   YES → Return True (full access)                                   │
│   NO  → Continue                                                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Map ptype to AC Action                                              │
│   ptype="write" → action="Write"                                    │
│   (capitalize first letter)                                         │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Call get_resource_rules()                                           │
│   - doctype: "Customer"                                             │
│   - action: "Write"                                                 │
│   - user: "user@example.com"                                        │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Get AC Rules for Customer + Write action                            │
│   - Check if resource is managed                                    │
│   - If unmanaged → Return None (fall through to Frappe permissions) │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Filter rules by user (Principal Filtering)                          │
│   - Check if user matches principal filters                         │
│   - Only keep rules where user matches principals                   │
│   - If no rules match → Return False (no access)                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Check if document matches resource filters                          │
│   - Build SQL query with resource filters                           │
│   - Check if document name matches the filters                      │
│   - Permit rules: Document must match at least one                  │
│   - Forbid rules: Document must not match any                       │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Return permission result                                            │
│   - True: User has permission                                       │
│   - False: User denied permission                                   │
│   - None: Unmanaged resource (fall through)                         │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frappe allows/denies access based on result                         │
│   (combined with other permission hooks)                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Permission Hook Chain

```
User action
    │
    ▼
┌──────────────────────────────────────┐
│ Frappe Permission System             │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Event Scripts Hook                   │  ← Deprecated
│ (if returns False → DENY)            │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Server Script Permission Policy Hook │  ← Deprecated
│ (if returns False → DENY)            │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ AC Rule Hook                         │  ← NEW!
│ (if returns False → DENY)            │
│ (if returns None → Continue)         │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Standard Frappe Permissions          │
│ (Role-based permissions)             │
└──────────┬───────────────────────────┘
           │
           ▼
      Allow/Deny
```

## Data Flow: Creating an AC Rule

```
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: Create Query Filters                                        │
│                                                                      │
│ Principal Filter (WHO)           Resource Filter (WHAT)             │
│ ┌────────────────────┐          ┌────────────────────┐             │
│ │ Sales Team Members │          │ Managed Customers  │             │
│ │ Type: JSON         │          │ Type: Python       │             │
│ │ DocType: User      │          │ DocType: Customer  │             │
│ │ Filter:            │          │ Filter:            │             │
│ │ dept = "Sales"     │          │ account_manager    │             │
│ │                    │          │ = current_user     │             │
│ └────────────────────┘          └────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 2: Create AC Resource                                          │
│                                                                      │
│ ┌────────────────────────────────────────────────────────────┐     │
│ │ AC Resource: Customer Access                                │     │
│ │ Type: DocType                                               │     │
│ │ Document Type: Customer                                     │     │
│ │ Managed Actions: Select                                     │     │
│ │ Actions: [Read, Write]                                      │     │
│ └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3: Create AC Rule                                              │
│                                                                      │
│ ┌────────────────────────────────────────────────────────────┐     │
│ │ AC Rule: Sales Team Customer Access                         │     │
│ │ Type: Permit                                                │     │
│ │ Resource: Customer Access                                   │     │
│ │ Actions: [Read, Write]                                      │     │
│ │ Principal Filters: [Sales Team Members]                     │     │
│ │ Resource Filters: [Managed Customers]                       │     │
│ └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Result: Automatic enforcement!                                      │
│                                                                      │
│ ✓ Sales team members see only their managed customers in lists     │
│ ✓ Sales team members can only access their managed customers       │
│ ✓ No additional code required                                      │
│ ✓ Works for all Customer accesses automatically                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Permission Type Mapping
```
Frappe ptype (lowercase)  →  AC Action (capitalized)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
read                      →  Read
write                     →  Write
create                    →  Create
delete                    →  Delete
submit                    →  Submit
cancel                    →  Cancel
```

### Access Levels
```
┌──────────┬─────────────────────────────────────────────────────────┐
│ Level    │ Description                                             │
├──────────┼─────────────────────────────────────────────────────────┤
│ total    │ User has access to ALL records (query = "1=1")         │
│ partial  │ User has conditional access (complex SQL query)        │
│ none     │ User has NO access (query = "1=0")                     │
│ unmanaged│ Resource not managed by AC Rules (empty query)         │
└──────────┴─────────────────────────────────────────────────────────┘
```

### Rule Logic
```
┌────────────────────────────────────────────────────────────────────┐
│ Permit Rules (Allow access to matching records)                   │
│   Final Filter = (Permit1 OR Permit2 OR ...)                      │
│                                                                    │
│ Forbid Rules (Deny access to matching records)                    │
│   Final Filter = NOT (Forbid1 OR Forbid2 OR ...)                  │
│                                                                    │
│ Combined:                                                          │
│   (Permit Rules) AND NOT (Forbid Rules)                           │
│                                                                    │
│ Note: Forbid takes precedence! If a record matches both Permit    │
│       and Forbid rules, access is DENIED.                         │
└────────────────────────────────────────────────────────────────────┘
```
