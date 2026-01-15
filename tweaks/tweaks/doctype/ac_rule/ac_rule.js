// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Rule", {
    setup(frm) {
        frm.trigger('setup_help');
        frm.trigger('setup_resource_filter_query');
    },
    refresh(frm) {
        frm.add_custom_button(__('Choose Actions'), () => {
            show_actions_dialog(frm);
        });
    },
    setup_help(frm) {
        frm.get_field('principals_html').html(`
            <p class="help-box small text-muted">
            This <code>rule</code> will apply to <code>users</code> <b>matching any</b> <code>filter</code> listed and <b>not matching any</b> <code>exception</code> listed
            <br><i>Example: (M1 OR M2) AND !(E1 OR E2)</i>
            </p>`
        );
        frm.get_field('resources_html').html(`
            <p class="help-box small text-muted">
            This <code>rule</code> will apply to <code>records</code> <b>matching any</b> <code>filter</code> listed and <b>not matching any</b> <code>exception</code> listed
            <br><i>Example: (M1 OR M2) AND !(E1 OR E2)</i>
            </p>
            <p class="help-box small text-muted">
            If <b>no</b> <code>filter</code> is defined, the <code>rule</code> will apply to <b>all records</b> of the specified <code>resource</code>.
            </p>
            `
        );
        frm.get_field('type_html').html(`
            <p class="help-box small text-muted">
            A <code>user</code> will have access to a <code>resource</code> if <b>at least one</b> <code>rule</code> permits it and <b>zero</b> <code>rules</code> forbid it.
            </p>`
        );
    },
    setup_resource_filter_query(frm) {
        frm.set_query('filter', 'resources', function() {
            if (!frm.doc.resource) {
                return {
                    filters: {
                        name: ['in', []]
                    }
                };
            }
            
            return {
                query: 'tweaks.tweaks.doctype.ac_rule.ac_rule.get_query_filters_for_resource',
                filters: {
                    resource: frm.doc.resource
                }
            };
        });
    },
    resource(frm) {
        frm.trigger('setup_resource_filter_query');
    }
});

function show_actions_dialog(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'AC Action',
            filters: {
                disabled: 0
            },
            fields: ['name', 'is_standard'],
            order_by: 'is_standard desc, name',
            limit_page_length: 0
        },
        callback(r) {
            if (!r.message || r.message.length === 0) {
                frappe.msgprint(__('No enabled AC Actions found'));
                return;
            }

            const actions = r.message;
            const current_actions = frm.doc.actions || [];
            
            // Separate standard and custom actions
            const standard_actions = actions.filter(a => a.is_standard);
            const custom_actions = actions.filter(a => !a.is_standard);
            
            // Further separate standard actions into groups
            const main_actions = ['Read', 'Write'];
            const operations_actions = ['Select', 'Create', 'Delete', 'Submit', 'Cancel', 'Amend'];
            
            const main_group = standard_actions.filter(a => main_actions.includes(a.name));
            const operations_group = standard_actions.filter(a => operations_actions.includes(a.name));
            const other_standard = standard_actions.filter(a => 
                !main_actions.includes(a.name) && !operations_actions.includes(a.name)
            );
            
            // Build fields dynamically
            const fields = [];
            
            // Add main actions section
            if (main_group.length > 0) {
                fields.push({
                    fieldtype: 'Section Break',
                    label: __('Main')
                });
                
                const items_per_column = Math.ceil(main_group.length / 2);
                main_group.forEach((action, idx) => {
                    if (idx > 0 && idx % items_per_column === 0) {
                        fields.push({
                            fieldtype: 'Column Break'
                        });
                    }
                    
                    fields.push({
                        fieldtype: 'Check',
                        fieldname: `main_action_${idx}`,
                        label: action.name,
                        default: current_actions.some(a => a.action === action.name) ? 1 : 0
                    });
                });
            }
            
            // Add operations actions section
            if (operations_group.length > 0) {
                fields.push({
                    fieldtype: 'Section Break',
                    label: __('Operations')
                });
                
                const items_per_column = Math.ceil(operations_group.length / 2);
                operations_group.forEach((action, idx) => {
                    if (idx > 0 && idx % items_per_column === 0) {
                        fields.push({
                            fieldtype: 'Column Break'
                        });
                    }
                    
                    fields.push({
                        fieldtype: 'Check',
                        fieldname: `operations_action_${idx}`,
                        label: action.name,
                        default: current_actions.some(a => a.action === action.name) ? 1 : 0
                    });
                });
            }
            
            // Add other standard actions section
            if (other_standard.length > 0) {
                fields.push({
                    fieldtype: 'Section Break',
                    label: __('Other')
                });
                
                const items_per_column = Math.ceil(other_standard.length / 2);
                other_standard.forEach((action, idx) => {
                    if (idx > 0 && idx % items_per_column === 0) {
                        fields.push({
                            fieldtype: 'Column Break'
                        });
                    }
                    
                    fields.push({
                        fieldtype: 'Check',
                        fieldname: `other_standard_action_${idx}`,
                        label: action.name,
                        default: current_actions.some(a => a.action === action.name) ? 1 : 0
                    });
                });
            }
            
            // Add custom actions section
            if (custom_actions.length > 0) {
                fields.push({
                    fieldtype: 'Section Break',
                    label: __('Custom')
                });
                
                const items_per_column = Math.ceil(custom_actions.length / 2);
                custom_actions.forEach((action, idx) => {
                    if (idx > 0 && idx % items_per_column === 0) {
                        fields.push({
                            fieldtype: 'Column Break'
                        });
                    }
                    
                    fields.push({
                        fieldtype: 'Check',
                        fieldname: `custom_action_${idx}`,
                        label: action.name,
                        default: current_actions.some(a => a.action === action.name) ? 1 : 0
                    });
                });
            }

            const dialog = new frappe.ui.Dialog({
                title: __('Choose Actions'),
                fields: fields,
                primary_action_label: __('Update Actions'),
                primary_action(values) {
                    const selected_actions = [];
                    
                    main_group.forEach((action, idx) => {
                        if (values[`main_action_${idx}`]) {
                            selected_actions.push({
                                action: action.name
                            });
                        }
                    });
                    
                    operations_group.forEach((action, idx) => {
                        if (values[`operations_action_${idx}`]) {
                            selected_actions.push({
                                action: action.name
                            });
                        }
                    });
                    
                    other_standard.forEach((action, idx) => {
                        if (values[`other_standard_action_${idx}`]) {
                            selected_actions.push({
                                action: action.name
                            });
                        }
                    });
                    
                    custom_actions.forEach((action, idx) => {
                        if (values[`custom_action_${idx}`]) {
                            selected_actions.push({
                                action: action.name
                            });
                        }
                    });

                    // Clear existing actions and add selected ones
                    frm.clear_table('actions');
                    selected_actions.forEach(action => {
                        frm.add_child('actions', action);
                    });
                    frm.refresh_field('actions');
                    
                    dialog.hide();
                }
            });

            dialog.show();
        }
    });
}
