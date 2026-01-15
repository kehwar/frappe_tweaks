// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings['AC Action'] = {
    onload(listview) {
        listview.page.add_inner_button(__('Create from Workflow Action Master'), () => {
            show_workflow_action_migration_dialog()
        })
    }
}

function show_workflow_action_migration_dialog() {
    frappe.call({
        method: 'tweaks.tweaks.doctype.ac_action.ac_action.get_workflow_actions_without_ac_action',
        callback(r) {
            if (!r.message || r.message.length === 0) {
                frappe.msgprint(__('All Workflow Action Masters already have corresponding AC Actions'))
                return
            }

            const workflow_actions = r.message
            
            // Build fields dynamically
            const fields = []
            
            workflow_actions.forEach((name, idx) => {
                fields.push({
                    fieldtype: 'Check',
                    fieldname: `action_${idx}`,
                    label: name,
                    default: 0
                })
            })

            const dialog = new frappe.ui.Dialog({
                title: __('Create AC Actions from Workflow Action Master'),
                fields: fields,
                primary_action_label: __('Create Selected'),
                primary_action(values) {
                    const selected_actions = []
                    
                    workflow_actions.forEach((name, idx) => {
                        if (values[`action_${idx}`]) {
                            selected_actions.push(name)
                        }
                    })

                    if (selected_actions.length === 0) {
                        frappe.msgprint(__('Please select at least one action to create'))
                        return
                    }

                    frappe.call({
                        method: 'tweaks.tweaks.doctype.ac_action.ac_action.create_ac_actions_from_workflow',
                        args: {
                            workflow_actions: selected_actions
                        },
                        callback(r) {
                            if (r.message) {
                                const { created, skipped } = r.message

                                let message = ''
                                if (created.length > 0) {
                                    message += `<p>${__('Created {0} AC Action(s):', [created.length])}</p><ul>`
                                    created.forEach((action) => {
                                        message += `<li>${action}</li>`
                                    })
                                    message += '</ul>'
                                }

                                if (skipped.length > 0) {
                                    message += `<p>${__('Skipped {0} action(s) (already exist or error):', [skipped.length])}</p><ul>`
                                    skipped.forEach((action) => {
                                        message += `<li>${action}</li>`
                                    })
                                    message += '</ul>'
                                }

                                frappe.msgprint(message)
                                dialog.hide()

                                // Refresh the listview
                                if (created.length > 0) {
                                    frappe.set_route('List', 'AC Action')
                                }
                            }
                        }
                    })
                }
            })

            dialog.show()
        }
    })
}
