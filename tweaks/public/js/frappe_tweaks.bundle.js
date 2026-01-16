import "../../custom/doctype/customer"

// Document Review Banner System
// Show pending reviews banner on form
function showPendingReviewsBanner(frm) {
    if (!frm.doc || !frm.doc.name) {
        return;
    }

    // Get doctypes with rules from bootinfo
    const doctypesWithRules = frappe.boot.additional_bootinfo?.doctypes_with_document_review_rules || [];

    // Check if this doctype has rules
    if (!doctypesWithRules.includes(frm.doctype)) {
        return;
    }

    // Get pending review count
    frappe.call({
        method: "tweaks.utils.document_review.get_pending_review_count",
        args: {
            doctype: frm.doctype,
            docname: frm.doc.name,
        },
        callback: (r) => {
            if (r.message && r.message > 0) {
                frm.set_intro(
                    __("This document has {0} pending review(s). Please review before proceeding.", [r.message]),
                    "orange"
                );
            }
        },
    });
}

// Register handler for all doctypes using wildcard
frappe.ui.form.on("*", {
    refresh: (frm) => {
        showPendingReviewsBanner(frm);
    },
});