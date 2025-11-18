// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Resource Filter", {
    refresh(frm) {
        frm.trigger("filters_type");
        frm.trigger("show_api_warning");
        
        // Add menu button to preview SQL
        if (!frm.is_new()) {
            frm.add_custom_button(__('Preview SQL'), function() {
                frappe.call({
                    method: 'get_sql',
                    doc: frm.doc,
                    callback: function(r) {
                        const d = new frappe.ui.Dialog({
                            title: __('SQL Preview'),
                            fields: [
                                {
                                    fieldtype: 'Code',
                                    fieldname: 'sql',
                                    label: __('SQL Preview'),
                                    options: 'SQL',
                                    default: r.message || ''
                                }
                            ],
                            primary_action_label: __('Close'),
                            primary_action: function() {
                                d.hide();
                            }
                        });
                        d.show();
                    }
                });
            });
        }
    },
    type(frm){
        frm.trigger("show_api_warning");
    },
    setup_python_help(frm) {
        frm.get_field('filters_help').html(`
            <p class="help-box small text-muted">
                Example:
                <code>
                conditions = f'tenant_id = {tenant_id}'
                </code>
            </p>`
        );
    },
    setup_sql_help(frm) {
        frm.get_field('filters_help').html(`
            <p class="help-box small text-muted">
                Example:
                <code>
                tenant_id = 1
                </code>
            </p>`
        );
    },
    setup_json_help(frm) {
        frm.get_field('filters_help').html(`
            <p class="help-box small text-muted">
                Example:
                <code>
                [["tenant_id", "=", 1]]
                </code>
            </p>`
        );
    },
    setup_filters_help(frm){
        if (frm.doc.filters_type == "SQL")
            frm.trigger('setup_sql_help');
        else if (frm.doc.filters_type == "JSON")
            frm.trigger('setup_json_help');
        else
            frm.trigger('setup_python_help');
    },
    filters_type(frm) {
        frm.trigger('setup_filters_help');
        frm.get_field('filters').df.options = frm.doc.filters_type || "Python";
        if (frm.get_field('filters').editor)
            frm.get_field('filters').set_language();
    },
});