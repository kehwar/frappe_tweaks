// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Resource", {
    setup(frm) {
        frm.trigger('setup_help');
    },
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Query Filters'), () => {
                if (frm.doc.type === 'DocType' && frm.doc.document_type) {
                    frappe.route_options = {
                        'reference_doctype': frm.doc.document_type
                    };
                } else if (frm.doc.type === 'Report' && frm.doc.report) {
                    frappe.route_options = {
                        'reference_report': frm.doc.report
                    };
                }
                
                frappe.set_route('List', 'Query Filter');
            }, "View");
        }
    },
    setup_help(frm) {
        frm.get_field('actions_html').html(`
            <p class="help-box small text-muted">
            A <code>user</code> will have access to this <code>resource</code> if <b>at least one</b> <code>rule</code> permits it and <b>zero</b> <code>rules</code> forbid it.
            <br>Unmanaged <code>actions</code> are not subject to any <code>rule</code> and are allowed by default.
            </p>`
        );
    }
});