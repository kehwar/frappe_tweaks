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
    },

    /**
     * Display a progress bar for a running batch of async tasks.
     *
     * Shows an indeterminate bar immediately, then updates it on every
     * `async_task_status` event that belongs to this batch. The server embeds
     * authoritative `batch_done` / `batch_total` counters (from Redis) in each
     * event, so the client owns no state — missed events are harmless.
     *
     * @param {string} batch_id   - Batch identifier returned by the server.
     * @param {string} [title]    - Progress bar title.
     * @param {function} [handler] - Called when all tasks are terminal with
     *   { batch_id, done, total }.
     */
    show_batch_progress: function (batch_id, title, handler) {
        if (!batch_id) {
            frappe.throw(__('batch_id is required.'))
        }

        const TERMINAL = ['Finished', 'Failed', 'Canceled']
        const dialog_title = title || __('Processing…')

        // Show an indeterminate bar immediately while we wait for the first event.
        frappe.show_progress(dialog_title, 0, 100, __('Starting…'))

        const _handler = ({ batch_id: evtBatchId, status, job_name, message: msg, batch_done, batch_total }) => {
            if (evtBatchId !== batch_id) return
            if (batch_total == null) return  // batch not yet registered in Redis — drop

            const description = msg || status
            frappe.show_progress(
                dialog_title,
                batch_done,
                batch_total,
                __('(Completed {0} of {1}) {2}: {3}', [batch_done, batch_total, job_name || '', description]),
                true,
            )

            if (TERMINAL.includes(status) && batch_done >= batch_total) {
                frappe.realtime.off('async_task_status', _handler)
                if (handler) {
                    handler({ batch_id, done: batch_done, total: batch_total })
                }
            }
        }

        frappe.realtime.on('async_task_status', _handler)
    },
})
