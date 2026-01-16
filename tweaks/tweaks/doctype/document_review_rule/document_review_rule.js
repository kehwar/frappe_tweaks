// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Document Review Rule", {
    refresh(frm) {
        frm.trigger("setup_script_help");
    },
    setup_script_help(frm) {
        frm.get_field('script_help').html(`
            <p class="help-box small text-muted">
                Return <code>None</code> if no review needed, or dict with <code>'message'</code> (str) and <code>'data'</code> (dict) keys.
                <br>Data should contain only values used to detect significant changes.
                <br><br>Example:
                <pre>if doc.grand_total &gt; 100000:
    return {
        "message": f"High value order: {frappe.utils.fmt_money(doc.grand_total)}",
        "data": {"total": doc.grand_total}
    }
return None</pre>
            </p>
        `);
    },
});
