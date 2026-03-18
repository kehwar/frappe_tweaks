## Session: 2026-03-18

### Summary

Skill was loaded to investigate a JS-side `TypeError: Cannot read properties of undefined (reading 'show_progress')` when calling `frappe.async_tasks.show_progress("dads")` in the browser console.

### Status

- Applied: yes

### Issues observed

#### Missing documentation — JS-side `frappe.async_tasks` namespace not documented

**Evidence**: The user hit a JS TypeError on `frappe.async_tasks.show_progress`. After loading the skill, its entire content covers the Python API (`enqueue_async_task`, `enqueue_safe_async_task`, etc.) and the server-side realtime event (`async_task_status`). There is no mention of `frappe.async_tasks` as a JS global, the `show_progress` helper, or that the namespace is provided by `tweaks/public/js/tweaks/async_tasks.js`. The agent had to discover the JS file independently via file search.

**Impact**: The skill gave no guidance on the JS API, so the agent had to fall back to manual grep work. A developer hitting the same error would find no help in the skill.

#### Ambiguity — Realtime JS snippet doesn't mention `frappe.async_tasks.show_progress`

**Evidence**: The skill documents listening for `async_task_status` with a raw `frappe.realtime.on(...)` snippet but never mentions that `frappe.async_tasks.show_progress` is a higher-level convenience wrapper around the same event that also drives `frappe.show_progress`. The two APIs are related but their relationship is undocumented.

**Impact**: Developers who see only the raw `realtime.on` example may re-implement `show_progress` manually instead of using the provided utility.
