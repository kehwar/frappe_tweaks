---
applyTo: "tweaks/doctype/sync_job_type/**, tweaks/doctype/sync_job/**, utils/sync_job.py, **/sync_job_type/**"
---

# Sync Job Framework

## Overview

The Sync Job framework provides a robust, queue-based system for synchronizing data between different DocTypes in Frappe/ERPNext. It handles the complete lifecycle of data synchronization including:

- Automatic retry logic with configurable delays
- Background job execution via RQ queues
- Detailed change tracking and diff generation
- Support for Insert, Update, and Delete operations
- Parent-child job relationships for batch operations
- Comprehensive logging and error handling

## Architecture

### Core Components

1. **Sync Job Type** - Defines the synchronization template
    - Source and Target DocTypes
    - Queue configuration (queue name, timeout, retry settings)
    - Associated Python module for sync logic

2. **Sync Job** - Individual synchronization task instance
    - Links to a Sync Job Type
    - References specific source and target documents
    - Tracks execution status, timing, and errors
    - Stores context data and change diffs

3. **Sync Job Module** - Python implementation (controller)
    - Contains the actual sync logic
    - Two modes: Bypass or Standard

## Execution Modes

### Bypass Mode (Full Control)

Implement a single `execute()` function for complete control over the sync process.

```python
def execute(sync_job, source_doc, context):
    """
    Execute sync job with full control
    
    Args:
        sync_job: Sync Job document
        source_doc: Source document
        context: Dict of context data
    
    Returns:
        Dict with keys:
            target_doc: Target document (saved or unsaved)
            operation: "insert", "update", or "delete"
            diff: Dict of changes (optional)
    """
    # Your custom logic here
    target_doc = frappe.get_doc("Target DocType", filters)
    
    # Make your changes
    target_doc.field = source_doc.field
    target_doc.save()
    
    return {
        "target_doc": target_doc,
        "operation": "update",
        "diff": {"field": {"old": old_value, "new": new_value}}
    }
```

**Use bypass mode when:**
- You need custom transaction handling
- Complex multi-document operations are required
- Standard workflow doesn't fit your use case

### Standard Mode (Framework-Handled)

Implement specific hook functions and let the framework handle the workflow.

#### Required Functions

```python
def get_target_document(sync_job, source_doc):
    """
    Get target document for sync
    
    Args:
        sync_job: Sync Job document (contains operation, context, flags)
        source_doc: Source document
    
    Returns:
        Tuple of (target_doc, operation)
        operation: "insert", "update", or "delete"
    """
    target_name = frappe.db.get_value("Target DocType", {"link_field": source_doc.name})
    
    if target_name:
        target_doc = frappe.get_doc("Target DocType", target_name)
        operation = "update"
    else:
        target_doc = frappe.new_doc("Target DocType")
        operation = "insert"
    
    return target_doc, operation


def update_target_doc(sync_job, source_doc, target_doc):
    """
    Update target document with data from source
    
    Args:
        sync_job: Sync Job document (contains operation and context)
        source_doc: Source document
        target_doc: Target document to update
    """
    target_doc.field1 = source_doc.field1
    target_doc.field2 = source_doc.field2
    # Framework will save automatically
```

#### Optional Functions

```python
def get_multiple_target_documents(sync_job, source_doc):
    """
    Return multiple targets (creates child jobs if > 1)
    
    NOTE: Do not return the doc object itself, as this will be serialized to new jobs.
    
    Returns:
        List of dicts with keys:
            target_document_type: DocType name of target
            target_document_name: Name of target document (None for insert operations)
            operation: "insert", "update", or "delete"
            context: Dict of context for this target (optional)
    """
    # Find existing target
    target1_name = frappe.db.get_value("Target DocType", {"link_field": source_doc.name})
    
    return [
        {
            "target_document_type": "Target DocType",
            "target_document_name": target1_name,  # Can be None for insert
            "operation": "update" if target1_name else "insert",
            "context": {"batch": 1}
        },
        {
            "target_document_type": "Another Target DocType",
            "target_document_name": None,  # None for insert operation
            "operation": "insert",
            "context": {"batch": 2}
        }
    ]


def before_sync(sync_job, source_doc, target_doc):
    """Hook called before sync (before save)"""
    pass


def after_sync(sync_job, source_doc, target_doc):
    """Hook called after sync (after save)"""
    pass
```

## Creating a Sync Job Type

### 1. Create via UI

Navigate to: **Sync Job Type > New**

Required fields:
- **Sync Job Type Name**: Descriptive name (e.g., "SAP Customer Sync")
- **Source Document Type**: DocType to sync from
- **Target Document Type**: DocType to sync to
- **Module**: Module for code organization (auto-set from source doctype)

Optional configuration:
- **Queue**: RQ queue name (default: "default")
- **Timeout**: Job timeout in seconds (default: 300)
- **Retry Delay**: Seconds between retries (default: 60)
- **Max Retries**: Maximum retry attempts (default: 3)

### 2. Implement Controller

When you save a standard Sync Job Type in developer mode, a boilerplate controller is created at:

```
{app}/{module}/sync_job_type/{scrubbed_name}/{scrubbed_name}.py
```

Example for "SAP Customer Sync" in Tweaks module:
```
tweaks/tweaks/sync_job_type/sap_customer_sync/sap_customer_sync.py
```

Edit this file to implement your sync logic using either bypass or standard mode.

## Enqueueing Sync Jobs

### From Python

```python
from tweaks.utils.sync_job import enqueue_sync_job

# Basic usage with document name
sync_job = enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_document_name="CUST-00001"
)

# Using document objects (automatically extracts type and name)
customer = frappe.get_doc("Customer", "CUST-00001")
sync_job = enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_doc=customer
)

# With target document object
customer = frappe.get_doc("Customer", "CUST-00001")
sap_customer = frappe.get_doc("SAP Customer", "SAP-001")
sync_job = enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_doc=customer,
    target_doc=sap_customer,
    operation="Update"
)

# With context and options
sync_job = enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_document_name="CUST-00001",
    context={"force_update": True, "batch_id": "BATCH-001"},
    operation="Update",  # Pre-specify operation
    target_document_type="SAP Customer",  # Pre-specify target type
    target_document_name="TARGET-001",  # Pre-specify target name
    queue="long",  # Override queue
    timeout=600,  # Override timeout
    trigger_type="API"  # How job was triggered
)
```

### From JavaScript

```javascript
frappe.call({
    method: 'tweaks.utils.sync_job.enqueue_sync_job',
    args: {
        sync_job_type: 'SAP Customer Sync',
        source_document_name: 'CUST-00001',
        context: {force_update: true}
    },
    callback: function(r) {
        console.log('Sync job created:', r.message.name);
    }
});
```

### Document Hooks

Trigger sync automatically on document events:

```python
# In hooks.py
doc_events = {
    "Customer": {
        "on_update": "myapp.utils.sync_customer"
    }
}

# In myapp/utils.py
def sync_customer(doc, method):
    from tweaks.utils.sync_job import enqueue_sync_job
    
    # Using document object directly
    enqueue_sync_job(
        sync_job_type="SAP Customer Sync",
        source_doc=doc,
        trigger_type="Document Hook"
    )
```

## Configuration Options

### Sync Job Type Level

These are defaults that can be overridden per job:

- **Queue**: Which RQ queue to use ("default", "short", "long")
- **Timeout**: Maximum execution time in seconds
- **Retry Delay**: Seconds to wait before retry
- **Max Retries**: Maximum retry attempts for failed jobs

### Sync Job Flags

Available on the `sync_job` object in your controller:

- `sync_job.insert_enabled` - Allow insert operations (default: True)
- `sync_job.update_enabled` - Allow update operations (default: True)
- `sync_job.delete_enabled` - Allow delete operations (default: True)
- `sync_job.update_without_changes_enabled` - Save even if no changes (default: False)

### Context Data

Pass custom data to your sync logic:

```python
enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_document_name="CUST-00001",
    context={
        "force_update": True,
        "sync_addresses": True,
        "batch_id": "BATCH-001"
    }
)

# Access in controller
def update_target_doc(sync_job, source_doc, target_doc):
    context = sync_job.get_context()
    if context.get("force_update"):
        # Force update logic
        pass
```

## Job Lifecycle

### Status Flow

1. **Pending** - Job created but not yet queued for execution
2. **Queued** - Job queued and waiting for worker
3. **Started** - Job picked up by worker and executing
4. **Finished** - Completed successfully
5. **Failed** - Error occurred (can retry if under max_retries)
6. **Canceled** - Manually canceled (only from Pending, Queued, or Failed status)
7. **Skipped** - No action taken (no changes detected or operation disabled)

### Automatic Retry

Failed jobs are automatically retried based on:
- `retry_count` < `max_retries`
- Current time >= `retry_after`

Retry schedule (exponential backoff):
```python
retry_after = now() + (retry_delay * (retry_count + 1))
```

Scheduler hook (`auto_retry_failed_jobs`) runs periodically to retry eligible jobs.

### Manual Retry

```python
sync_job = frappe.get_doc("Sync Job", job_name)
sync_job.retry()  # Resets status to Queued and re-enqueues
```

### Cancellation

```python
sync_job = frappe.get_doc("Sync Job", job_name)
sync_job.cancel_sync(reason="No longer needed")
```

### Dry Run Mode

Jobs can be configured to run in dry run mode, which calculates the diff without actually saving any changes:

```python
# Enqueue job with dry run enabled
sync_job = enqueue_sync_job(
    sync_job_type="SAP Customer Sync",
    source_document_name="CUST-00001",
    dry_run=True  # Calculate diff but don't save
)

# After execution, job will have status "Finished"
# Review the diff_summary field to see what changes would be made
```

**Use dry run mode when:**
- Testing sync configurations before applying them
- Validating what changes will be made without committing them
- Auditing sync operations
- Debugging sync logic

**How it works:**
1. Job executes normally until the diff is calculated
2. The `diff_summary` field is populated with proposed changes
3. Job skips the save operation and all hooks (before_sync, after_sync)
4. Status is set to "Finished" without making any actual changes
5. You can review the diff to see what would have happened

## Advanced Features

### Parent-Child Jobs

For batch operations, create child jobs:

```python
# In controller's get_multiple_target_documents()
def get_multiple_target_documents(sync_job, source_doc):
    targets = []
    for child in source_doc.get("items"):
        target = frappe.get_doc("Target Item", {"source_id": child.name})
        targets.append({
            "target_doc": target,
            "operation": "update",
            "context": {"line_number": child.idx}
        })
    return targets
```

Framework automatically creates child sync jobs for each target (if > 1).

### Change Tracking

The framework automatically generates diffs for updates:

```python
# Stored in sync_job.diff_summary
{
    "field1": {"old": "value1", "new": "value2"},
    "field2": {"old": 100, "new": 200}
}
```

Access via:
- `sync_job.diff_summary` - JSON string of changes
- `sync_job.current_data` - Snapshot before sync
- `sync_job.updated_data` - Snapshot after sync

### Error Handling

Errors are captured with full traceback:

```python
sync_job.error_message  # Contains full error details
sync_job.status         # Set to "Failed"
```

View errors in:
- Sync Job document
- Error Log (if error logging enabled)
- Background Jobs list

## Examples

### Example 1: Simple Customer Sync

```python
# tweaks/tweaks/sync_job_type/sap_customer_sync/sap_customer_sync.py

def get_target_document(sync_job, source_doc):
    """Find or create customer in SAP"""
    sap_id = frappe.db.get_value("SAP Customer", {"erp_customer": source_doc.name})
    
    if sap_id:
        target_doc = frappe.get_doc("SAP Customer", sap_id)
        operation = "update"
    else:
        target_doc = frappe.new_doc("SAP Customer")
        target_doc.erp_customer = source_doc.name
        operation = "insert"
    
    return target_doc, operation


def update_target_doc(sync_job, source_doc, target_doc):
    """Map fields from Customer to SAP Customer"""
    target_doc.customer_name = source_doc.customer_name
    target_doc.customer_type = source_doc.customer_type
    target_doc.customer_group = source_doc.customer_group
    target_doc.territory = source_doc.territory
```

### Example 2: Delete Operation

```python
def get_target_document(sync_job, source_doc):
    """Delete customer from SAP"""
    sap_id = frappe.db.get_value("SAP Customer", {"erp_customer": source_doc.name})
    
    if sap_id:
        target_doc = frappe.get_doc("SAP Customer", sap_id)
        operation = "delete"
    else:
        # No target found, nothing to delete
        target_doc = None
        operation = "delete"
    
    return target_doc, operation


def update_target_doc(sync_job, source_doc, target_doc):
    """No updates needed for delete"""
    pass
```

### Example 3: Bypass Mode with External API

```python
def execute(sync_job, source_doc, context):
    """Sync to external API"""
    import requests
    
    # Call external API
    response = requests.post(
        "https://api.example.com/customers",
        json={
            "name": source_doc.customer_name,
            "email": source_doc.email_id
        }
    )
    
    if response.ok:
        # Update local tracking record
        external_id = response.json()["id"]
        target_doc = frappe.get_doc("External Customer", source_doc.name)
        target_doc.external_id = external_id
        target_doc.last_synced = now()
        target_doc.save()
        
        return {
            "target_doc": target_doc,
            "operation": "update"
        }
    else:
        frappe.throw(f"API Error: {response.text}")
```

### Example 4: Conditional Sync with Context

```python
def get_target_document(sync_job, source_doc):
    """Conditional sync based on context"""
    context = json.loads(sync_job.context) if sync_job.context else {}
    
    # Only sync if customer is active or force_update is set
    if not source_doc.disabled or context.get("force_update"):
        sap_id = frappe.db.get_value("SAP Customer", {"erp_customer": source_doc.name})
        
        if sap_id:
            return frappe.get_doc("SAP Customer", sap_id), "update"
        else:
            target = frappe.new_doc("SAP Customer")
            target.erp_customer = source_doc.name
            return target, "insert"
    
    return None, None  # Skip sync


def update_target_doc(sync_job, source_doc, target_doc):
    """Update with context-aware logic"""
    context = json.loads(sync_job.context) if sync_job.context else {}
    
    target_doc.customer_name = source_doc.customer_name
    
    # Only sync addresses if requested
    if context.get("sync_addresses"):
        sync_addresses(source_doc, target_doc)
```

## Best Practices

1. **Use Standard Mode** for simple field mappings
2. **Use Bypass Mode** for complex operations or external integrations
3. **Always validate** source and target documents before syncing
4. **Handle missing targets** gracefully (return None or create new)
5. **Use context** to pass runtime parameters instead of hardcoding
6. **Log important decisions** using `frappe.log_error()` for debugging
7. **Set appropriate timeouts** based on operation complexity
8. **Use specific queues** for heavy operations ("long" queue)
9. **Test retry logic** by intentionally failing jobs
10. **Monitor job status** regularly to catch systemic issues

## Troubleshooting

### Job Stays in Queued Status

- Check if RQ workers are running (`bench worker`)
- Verify queue name is correct
- Check for RQ connection issues

### Job Fails Repeatedly

- Check `error_message` field for details
- Verify source and target documents exist
- Ensure module path is correct
- Check for missing dependencies

### No Changes Detected (Skipped)

- Verify `update_without_changes_enabled` flag
- Check if diff generation is working
- Review your `update_target_doc()` logic

### Module Not Found

- Ensure controller file exists at correct path
- Check module naming (must use scrubbed names)
- Verify `is_standard = "Yes"` and developer mode enabled
- Run `bench migrate` to ensure exports completed

## API Reference

### enqueue_sync_job()

```python
from tweaks.utils.sync_job import enqueue_sync_job

sync_job = enqueue_sync_job(
    sync_job_type,              # Required: Sync Job Type name
    source_document_name,       # Required: Source document name
    context=None,               # Optional: Dict of context data
    operation=None,             # Optional: "Insert", "Update", or "Delete"
    target_document_name=None,  # Optional: Pre-specify target
    parent_sync_job=None,       # Optional: Parent job name
    queue=None,                 # Optional: Override queue
    timeout=None,               # Optional: Override timeout
    retry_delay=None,           # Optional: Override retry delay
    max_retries=None,           # Optional: Override max retries
    trigger_type="Manual",      # Optional: Trigger source
    dry_run=False               # Optional: Calculate diff without saving
)
```

### Controller Function Signatures

```python
# Bypass Mode
def execute(sync_job, source_doc, context) -> dict

# Standard Mode - Required
def get_target_document(sync_job, source_doc) -> tuple[Document|None, str|None]
def update_target_doc(sync_job, source_doc, target_doc) -> None

# Standard Mode - Optional
def get_multiple_target_documents(sync_job, source_doc) -> list[dict]
def before_sync(sync_job, source_doc, target_doc) -> None
def after_sync(sync_job, source_doc, target_doc) -> None
```

## Scheduler Integration

Add to `hooks.py` for automatic retry:

```python
scheduler_events = {
    "cron": {
        "*/5 * * * *": [  # Every 5 minutes
            "tweaks.utils.sync_job.auto_retry_failed_jobs"
        ]
    }
}
```

## Log Cleanup

Sync Jobs are logged documents. Configure cleanup in **Log Settings**:

```python
# Or programmatically
SyncJob.clear_old_logs(days=30)
```

## Permissions

- **Sync Job Type**: Requires Script Manager role (or Administrator for standard types)
- **Sync Job**: Typically system-managed, but can be viewed by users with appropriate roles
- **Target Documents**: Sync jobs run with `ignore_permissions=True`, ensure proper validation in controllers

---

For more information, refer to the source code:
- `tweaks/utils/sync_job.py` - Utility functions
- `tweaks/tweaks/doctype/sync_job_type/` - Sync Job Type DocType
- `tweaks/tweaks/doctype/sync_job/` - Sync Job DocType
