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

    // Check additional timeline content for pending reviews
    const additionalContent = frm.timeline?.doc_info?.additional_timeline_content || [];
    const pendingReviews = additionalContent.filter(
        (item) => item.template_data?.doc?.review_docstatus === 0
    );
    
    if (pendingReviews.length > 0) {
        frm.set_intro(
            __("This document has {0} pending review(s). Please review before proceeding.", [pendingReviews.length]),
            "orange"
        );
    }
}

// Register handler for all doctypes using wildcard
frappe.ui.form.on("*", {
    refresh: (frm) => {
        showPendingReviewsBanner(frm);
    },
});