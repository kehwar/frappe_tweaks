// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Rule", {
    setup(frm) {
        frm.trigger('setup_help');
        frm.trigger('setup_resource_filter_query');
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


