---
name: document-review-expert
description: Expert guidance for creating, implementing, and troubleshooting Document Review Rules in Frappe Tweaks - a flexible document review/approval system. Use when working with Document Review Rules, Document Reviews, implementing review/approval workflows, creating validation scripts, debugging review issues, understanding review evaluation and lifecycle, or integrating reviews with workflows and submissions.
---

# Document Review Expert

Expert guidance for working with the Document Review system in Frappe Tweaks, a flexible document review/approval framework.

## Overview

The Document Review system provides a rule-based approach to document validation and approval workflows:

- **Document Review Rules** define validation checks via Python scripts
- **Document Reviews** track approval state as submittable records
- Rules are evaluated automatically on document changes
- Mandatory reviews block document submission
- Reviews integrate with workflows and timeline

This system enables dynamic approval requirements based on document content, bypassing the need for complex workflow configurations.

## Core Concepts

### Document Review Rule

A rule that defines when a document needs review via a Python script. The script:
- Has access to `doc` variable (the document being checked)
- Returns `None` if no review needed
- Returns a dict with `message` and optional `data` if review is required

**Key properties:**
- `title`: Human-readable rule name
- `reference_doctype`: DocType this rule applies to
- `script`: Python code to evaluate (see [Script Writing Guide](references/script-examples.md))
- `mandatory`: If checked, blocks submission until review is approved
- `disabled`: Temporarily disable the rule

### Document Review

A submittable record representing a required review. Created automatically when a rule returns a result.

**Lifecycle:**
1. **Draft (docstatus=0)**: Pending review, blocks submission if mandatory
2. **Submitted (docstatus=1)**: Approved, allows submission
3. **Cancelled (docstatus=2)**: Rejected

**Key properties:**
- `reference_doctype` + `reference_name`: Link to the document being reviewed
- `review_rule`: Link to the rule that created this review
- `message`: Explanation of why review is needed
- `review_data`: Additional structured data (JSON)
- `mandatory`: Whether this review blocks submission

### Evaluation Lifecycle

Rules are evaluated automatically via hooks:

1. **on_change**: Evaluates all rules for the doctype when document changes
2. **before_submit**: Checks for pending mandatory reviews, blocks if found
3. **Timeline integration**: Displays reviews in document timeline with action buttons

## Quick Start

### Creating a Basic Review Rule

1. Navigate to **Document Review Rule** list
2. Create new rule with:
   - **Title**: Descriptive name (e.g., "Check Minimum Price")
   - **Reference DocType**: Target DocType (e.g., "Sales Order")
   - **Script**: Python code that returns `None` or review dict
   - **Mandatory**: Check if submission should be blocked

Example script:
```python
# Check if total is above threshold
if doc.grand_total > 100000:
    result = {
        "message": "Order exceeds approval threshold of $100,000",
        "data": {
            "grand_total": doc.grand_total,
            "threshold": 100000
        }
    }
```

3. Save the rule - it takes effect immediately

### Reviewing a Document

When a Document Review is created:

1. Document owner sees review in timeline with "Review" button
2. Reviewer clicks "Review" button
3. Review dialog opens with approval/rejection options
4. Submit review to approve, Cancel to reject

## Common Use Cases

### 1. Price Approval

Require manager approval for items below minimum price.

See [references/script-examples.md](references/script-examples.md) for complete example.

### 2. Credit Limit Check

Flag orders that exceed customer credit limit.

### 3. Discount Approval

Require approval for discounts above certain percentage.

### 4. Compliance Checks

Verify required fields, attachments, or certifications.

### 5. Multi-level Approvals

Different rules for different approval thresholds.

## Integration Patterns

### With Workflows

Use reviews as workflow transition conditions:

```python
# In Workflow Transition condition
frappe.db.count("Document Review", {
    "reference_doctype": doc.doctype,
    "reference_name": doc.name,
    "docstatus": 0
}) == 0
```

See [references/integration-patterns.md](references/integration-patterns.md) for detailed examples.

### With Form Banners

Display pending review count using Client Scripts:

```javascript
frappe.call({
    method: "frappe.client.get_count",
    args: {
        doctype: "Document Review",
        filters: {
            reference_doctype: frm.doctype,
            reference_name: frm.docname,
            docstatus: 0
        }
    },
    callback: (r) => {
        if (r.message > 0) {
            frm.dashboard.add_indicator(
                __("Pending Reviews: {0}", [r.message]),
                "orange"
            );
        }
    }
});
```

### With Server Scripts

Create or check reviews programmatically. See [references/integration-patterns.md](references/integration-patterns.md).

## Rule Writing Guide

### Script Context

The rule script has access to:
- `doc`: The document instance being evaluated
- Standard Frappe API: `frappe.db.get_value()`, `frappe.get_all()`, etc.
- All standard Python functions

### Return Format

**No review needed:**
```python
result = None
```

**Review required:**
```python
result = {
    "message": "Explanation of why review is needed",
    "data": {
        # Optional structured data for reviewers
        "field1": value1,
        "field2": value2
    }
}
```

### Best Practices

1. **Early exit**: Return `None` as soon as possible when no review needed
2. **Clear messages**: Explain why review is needed and what to check
3. **Include data**: Provide context in `data` field for reviewers
4. **Handle errors**: Use try-except to prevent script failures
5. **Performance**: Minimize database queries, use caching when appropriate

See [references/script-examples.md](references/script-examples.md) for complete examples.

## Reference Files

Detailed guides for specific topics:

- **[references/document-review-system.md](references/document-review-system.md)**: Complete system architecture and lifecycle
- **[references/rule-creation-guide.md](references/rule-creation-guide.md)**: Step-by-step guide to creating rules
- **[references/script-examples.md](references/script-examples.md)**: Working script examples for common scenarios
- **[references/integration-patterns.md](references/integration-patterns.md)**: Workflow, form, and programmatic integration
- **[references/troubleshooting.md](references/troubleshooting.md)**: Common issues and debugging techniques

## Key Features

### Automatic Evaluation

Rules run automatically on document save via `on_change` hook. No manual triggering required.

### Smart Review Management

- Draft reviews auto-created when rule returns result
- Auto-deleted when rule no longer applies (returns `None`)
- Prevents duplicate reviews for same data
- Reuses submitted reviews if data hasn't changed

### Timeline Integration

Reviews appear in document timeline with:
- Status indicators (Pending/Approved/Rejected)
- Review messages with formatted data
- Action buttons for pending reviews
- Full audit trail

### Permission Control

Reviews respect standard Frappe permissions:
- Only users with submit permission can approve reviews
- System Managers have full access by default
- Custom roles can be configured

## Troubleshooting

**Rule not triggering:**
- Check if rule is disabled
- Verify `reference_doctype` matches document type
- Clear cache: `frappe.cache.delete_value(f"document_review_rules:{doctype}")`

**Script errors:**
- Check error log: `bench --site [site] logs`
- Use try-except in script for debugging
- Test script logic in Python console first

**Review not blocking submission:**
- Verify `mandatory` is checked on rule
- Check review `docstatus` (must be 0 to block)
- Ensure `before_submit` hook is configured

See [references/troubleshooting.md](references/troubleshooting.md) for comprehensive debugging guide.

## API Reference

### Functions

**`get_rules_for_doctype(doctype)`**
Get all active rules for a doctype (cached).

**`evaluate_document_reviews(doc, method=None)`**
Evaluate all rules for a document (called by `on_change` hook).

**`check_mandatory_reviews(doc, method=None)`**
Block submission if mandatory reviews pending (called by `before_submit` hook).

**`submit_document_review(review_name, review=None, action="approve")`**
Whitelist function to submit/cancel a review.

### Hooks Configuration

```python
doc_events = {
    "*": {
        "on_change": ["tweaks.utils.document_review.evaluate_document_reviews"],
        "before_submit": ["tweaks.utils.document_review.check_mandatory_reviews"],
    }
}

additional_timeline_content = {
    "*": ["tweaks.utils.document_review.get_document_reviews_for_timeline"]
}

get_additional_bootinfo = [
    "tweaks.utils.document_review.add_document_review_bootinfo"
]
```

## Performance Considerations

- Rules cached per doctype (invalidated on rule changes)
- Evaluation runs only on document change
- Timeline queries optimized with proper indexes
- Review data comparison prevents duplicate reviews

## Security Notes

- Scripts run with full permissions in safe_exec context
- Reviews created with `ignore_permissions=True`
- Always validate user input in scripts
- Be cautious with database modifications in scripts
