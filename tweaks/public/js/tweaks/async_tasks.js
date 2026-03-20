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

    /**
     * Track a two-phase operation: a coordinator task followed by a batch of
     * async tasks fanned out by that coordinator.
     *
     * Phase 1: Shows a single-task progress bar for the coordinator task via
     *   show_progress. A listener for the `async_batch_enqueued` realtime event
     *   with matching batch_id is registered in parallel.
     *
     * Phase 2: Once the batch is known (total received via async_batch_enqueued),
     *   each terminal `async_task_status` event for the batch advances the count.
     *   When all tasks reach a terminal state handler is called with a summary.
     *
     * @param {string} batch_id      - Batch identifier returned by the server.
     * @param {string} coordinator_task_name - Async Task Log name of the coordinator.
     * @param {string} [title]       - Progress bar title.
     * @param {function} [handler]   - Called on each batch task event AND on
     *   completion with { batch_id, finished, failed, canceled, total }.
     */
    show_batch_progress: function (batch_id, coordinator_task_name, title, handler) {
        if (!batch_id) {
            frappe.throw(__('batch_id is required.'))
        }
        if (!coordinator_task_name) {
            frappe.throw(__('coordinator_task_name is required.'))
        }

        const TERMINAL = ['Finished', 'Failed', 'Canceled']
        const dialog_title = title || __('Processing…')

        // Per-batch counters — populated once async_batch_enqueued fires.
        let batchTotal = null
        let finished = 0
        let failed = 0
        let canceled = 0

        const _checkBatchComplete = () => {
            const done = finished + failed + canceled
            if (done >= batchTotal) {
                frappe.realtime.off('async_task_status', _batchHandler)
                frappe.realtime.off('async_batch_enqueued', _batchEnqueuedHandler)
                if (handler) {
                    handler({ batch_id, finished, failed, canceled, total: batchTotal })
                }
            }
        }

        // Phase 2: listen for individual task completions
        const _batchHandler = ({ batch_id: evtBatchId, status }) => {
            if (evtBatchId !== batch_id) return
            if (!TERMINAL.includes(status)) return
            if (batchTotal === null) return  // shouldn't happen, but guard

            if (status === 'Finished') finished++
            else if (status === 'Failed') failed++
            else if (status === 'Canceled') canceled++

            const done = finished + failed + canceled
            frappe.show_progress(
                dialog_title,
                done,
                batchTotal,
                __('Processing {0} of {1}', [done, batchTotal]),
                true,
            )
            _checkBatchComplete()
        }

        // Phase 1 → Phase 2 transition: batch is now known
        const _batchEnqueuedHandler = ({ batch_id: evtBatchId, total }) => {
            if (evtBatchId !== batch_id) return
            frappe.realtime.off('async_batch_enqueued', _batchEnqueuedHandler)

            batchTotal = total
            frappe.show_progress(dialog_title, 0, total, __('Processing 0 of {0}', [total]), true)

            // Check if any tasks already finished before we registered
            _checkBatchComplete()
        }

        // Register Phase 2 listeners immediately — before the coordinator
        // even runs — so no events are missed.
        frappe.realtime.on('async_batch_enqueued', _batchEnqueuedHandler)
        frappe.realtime.on('async_task_status', _batchHandler)

        // Phase 1: track the coordinator using the single-task helper.
        // When the coordinator finishes it will have already called
        // bulk_enqueue_async_task which emits async_batch_enqueued.
        frappe.async_tasks.show_progress(
            coordinator_task_name,
            dialog_title,
            ({ status, error }) => {
                if (status === 'Failed') {
                    // Coordinator failed — clean up batch listeners.
                    frappe.realtime.off('async_batch_enqueued', _batchEnqueuedHandler)
                    frappe.realtime.off('async_task_status', _batchHandler)
                }
                if (handler) {
                    handler({ coordinator_status: status, error })
                }
            },
        )
    },
})
