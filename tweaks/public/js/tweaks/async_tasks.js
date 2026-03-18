frappe.provide("frappe.async_tasks")

$.extend(frappe.async_tasks, {
    show_progress: function (name, title, handler) {
        if (!name) {
            frappe.throw(__('Task name is required.'))
        }

        const steps = {
            Pending: { pct: 10, label: __('Pending') },
            Queued: { pct: 40, label: __('Queued') },
            Started: { pct: 70, label: __('Running') },
            Finished: { pct: 100, label: __('Finished') },
            Failed: { pct: 100, label: __('Failed') },
            Canceled: { pct: 100, label: __('Canceled') },
        }

        let dialog_title = title || __('Task {0}', [name])

        frappe.show_progress(dialog_title, 10, 100, __('Pending'))

        const TERMINAL = ['Finished', 'Failed', 'Canceled']

        const _handler = ({ name: taskName, status, message: msg, error: err }) => {
            if (taskName !== name)
                return
            const s = steps[status] || { pct: 10, label: status }
            let progressCount = s.pct
            let progressTotal = 100
            let progressLabel = msg || s.label
            if (msg && typeof msg === 'object' && msg.progress) {
                const p = msg.progress
                if (p.count != null) progressCount = p.count
                if (p.total != null) progressTotal = p.total
                if (p.description != null) progressLabel = p.description
            }
            frappe.show_progress(dialog_title, progressCount, progressTotal, progressLabel, true)
            if (TERMINAL.includes(status)) {
                frappe.realtime.off('async_task_status', _handler)
                if (status === 'Failed') {
                    frappe.throw(err || __('Task failed with an unknown error.'))
                }
            }
            if (handler) {
                handler({ name: taskName, status, message: msg, error: err })
            }
        }

        // Register listener first so we don't miss an event that fires
        // during the initial status fetch below.
        frappe.realtime.on('async_task_status', _handler)

        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Async Task Log',
                filters: { name: name },
                fieldname: 'status',
            },
            callback(r) {
                const status = r.message?.status
                if (!status) {
                    // Task doesn't exist – clean up and report the error.
                    frappe.realtime.off('async_task_status', _handler)
                    frappe.show_progress(dialog_title, 100, 100, __('Task {0} not found.', [name]), false)
                    return
                }
                if (TERMINAL.includes(status)) {
                    // Already finished before we registered – handle it now.
                    _handler({ name: name, status, message: null })
                } else {
                    // In progress – sync the bar to the current status.
                    const s = steps[status] || { pct: 10, label: status }
                    frappe.show_progress(dialog_title, s.pct, 100, s.label, true)
                }
            },
        })
    },
})
