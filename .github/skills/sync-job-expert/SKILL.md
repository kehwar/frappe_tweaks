---
name: sync-job-expert
description: Expert guidance for creating, implementing, and troubleshooting Sync Jobs in the Frappe Tweaks framework. Use when working with Sync Job Types, Sync Job controllers, sync job enqueueing, debugging sync job issues, implementing sync logic, or understanding sync job lifecycle and hooks.
---

# Sync Job Expert

Expert guidance for the Frappe Tweaks Sync Job framework - a queue-based system for data synchronization between DocTypes.

## Core Concepts

**Sync Job Type**: Template defining sync configuration (source/target doctypes, queue, timeout, retry settings)  
**Sync Job**: Individual task instance tracking execution, status, errors, and diffs  
**Controller**: Python module implementing sync logic (Bypass or Standard mode)

## Quick Start

### Creating a Sync Job Type

1. Navigate to **Sync Job Type > New**
2. Set name, source doctype, target doctype
3. Save (in developer mode, creates controller at `{app}/{module}/sync_job_type/{scrubbed_name}/{scrubbed_name}.py`)
4. Implement sync logic in controller

### Enqueue a Sync Job

```python
from tweaks.utils.sync_job import enqueue_sync_job

sync_job = enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_document_name="CUST-00001",
    context={"force_update": True}
)
```

## Implementation Modes

### Standard Mode (Recommended)

Framework handles workflow. Implement these hooks:

**Required:**
- `get_target_document(sync_job, source_doc)` - Return target metadata dict
- `update_target_doc(sync_job, source_doc, target_doc)` - Update target fields

**Optional:**
- `get_multiple_target_documents()` - Return list of targets (creates child jobs if > 1)
- `after_start()` - Initialize before sync
- `before_relay()/after_relay()` - Handle batch operations
- `before_sync()/after_sync()` - Pre/post save hooks
- `finished()` - Post-processing after success

### Bypass Mode (Advanced)

Full control over sync process. Implement:

```python
def execute(sync_job, source_doc):
    """Returns dict: {target_doc, operation, diff}"""
    pass
```

## Controller Patterns

### Standard Mode - Insert or Update

```python
def get_target_document(sync_job, source_doc):
    target_name = frappe.db.get_value("SAP Customer", {"erp_customer": source_doc.name})
    
    if target_name:
        return {
            "operation": "update",
            "target_document_name": target_name
        }
    else:
        return {
            "operation": "insert"
        }

def update_target_doc(sync_job, source_doc, target_doc):
    if not target_doc.erp_customer:
        target_doc.erp_customer = source_doc.name
    target_doc.customer_name = source_doc.customer_name
```

### Multiple Targets (Batch Operations)

```python
def get_multiple_target_documents(sync_job, source_doc):
    targets = []
    for item in source_doc.get("items"):
        target_name = frappe.db.get_value("Target Item", {"source_id": item.name})
        targets.append({
            "target_document_type": "Target Item",
            "target_document_name": target_name,
            "operation": "update" if target_name else "insert",
            "context": {"line_number": item.idx}
        })
    return targets
```

### Conditional Sync with Context

```python
def get_target_document(sync_job, source_doc):
    context = sync_job.get_context()
    
    if not source_doc.disabled or context.get("force_update"):
        # Return target info...
        return {"operation": "update", "target_document_name": "..."}
    
    # Skip sync
    return {"operation": "insert", "target_document_type": None}
```

### Deleted Source Handling

When source is deleted, `source_doc` is None. Use context to pass data:

```python
def get_multiple_target_documents(sync_job, source_doc):
    context = sync_job.get_context()
    component_names = context.get("component_names", [])
    
    targets = []
    for name in component_names:
        targets.append({
            "target_document_type": "Item",
            "target_document_name": name,
            "operation": "update",
            "context": {"clear_properties": True}
        })
    return targets

def update_target_doc(sync_job, source_doc, target_doc):
    if source_doc is None:
        context = sync_job.get_context()
        if context.get("clear_properties"):
            target_doc.is_bundle_component = 0
```

## Status Flow

1. **Pending** → 2. **Queued** → 3. **Started** → **Finished/Failed/Skipped/Relayed/No Target**
- **Canceled**: Manual cancel (from Pending/Queued/Failed)
- **Failed**: Retries automatically if `retry_count < max_retries`

## Key Methods

**On sync_job:**
- `sync_job.get_context()` - Parse context dict
- `sync_job.get_source_document()` - Load source (even if deleted)
- `sync_job.get_trigger_document()` - Load triggering document
- `sync_job.get_target_document()` - Load target

**Flags (control operations):**
- `sync_job.insert_enabled/update_enabled/delete_enabled`
- `sync_job.update_without_changes_enabled`
- `sync_job.dry_run` - Calculate diff without saving

## Configuration

**Sync Job Type defaults (can override per job):**
- Queue: "default", "short", "long"
- Timeout: seconds
- Retry Delay: seconds between retries
- Max Retries: maximum attempts
- Verbose Logging: preserve data snapshots (disabled by default)

**Context**: Pass custom data to sync logic
**Trigger Tracking**: Track what triggered the job for auditing

## Dry Run Mode

Test sync without changes:

```python
sync_job = enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_document_name="CUST-00001",
    dry_run=True  # Populates diff_summary without saving
)
```

## Troubleshooting

**Job stays Queued**: Check RQ workers running (`bench worker`), verify queue name  
**Job fails repeatedly**: Check `error_message`, verify documents exist, validate module path  
**No changes detected**: Set `update_without_changes_enabled=True` or check diff generation  
**Module not found**: Ensure controller exists, check naming (use scrubbed names), run `bench migrate`

## Best Practices

1. Use Standard Mode for simple mappings, Bypass for complex operations
2. Validate source/target before syncing
3. Handle missing targets gracefully (return `target_document_type=None`)
4. Use context for runtime parameters
5. Set appropriate timeouts for operation complexity
6. Use specific queues for heavy operations
7. Log important decisions with `frappe.log_error()`
8. Test retry logic with intentional failures

## Source Code References

- `tweaks/utils/sync_job.py` - Core utilities
- `tweaks/tweaks/doctype/sync_job_type/` - Sync Job Type DocType
- `tweaks/tweaks/doctype/sync_job/` - Sync Job DocType
- `tweaks/tweaks/doctype/sync_job_type/boilerplate/controller._py` - Controller template
