// Document Review Banner System
// Show pending reviews banner on form
function showPendingReviewsBanner(frm) {
    if (!frm.doc || !frm.doc.name) {
        return;
    }

    if (frm.doc.__islocal){
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
        frm.set_intro();
        frm.set_intro(
            __("This document has {0} pending review(s).", [pendingReviews.length]),
            "orange"
        );
        
        // Add button to scroll to reviews
        frm.add_custom_button(__("See Pending Reviews"), () => {
            const firstPendingReview = frm.footer.wrapper.find('[data-communication-type="Document Review::0"]').first();
            if (firstPendingReview.length) {
                frappe.utils.scroll_to(firstPendingReview);
            }
        });
    }
}

// Submit review handler
function submitReview(frm, reviewName, review, action) {
    frappe.call({
        method: "tweaks.utils.document_review.submit_document_review",
        args: { 
            review_name: reviewName,
            review: review,
            action: action
        },
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert({
                    message: action === "approve" ? __("Review approved") : __("Review rejected"),
                    indicator: action === "approve" ? "green" : "red"
                });
                frm.reload_doc();
            }
        }
    });
}

// Register handler for all doctypes using wildcard
frappe.ui.form.on("*", {
    refresh: (frm) => {
        showPendingReviewsBanner(frm);
    },
    document_review_approve: (frm, reviewName) => {
        // Show dialog for review with Approve/Reject options
        const dialog = new frappe.ui.Dialog({
            title: __("Complete Review"),
            fields: [
                {
                    fieldname: "review",
                    fieldtype: "Text Editor",
                    label: __("Review Comments"),
                    description: __("Add any comments or notes about this review")
                }
            ],
            primary_action_label: __("Approve"),
            primary_action: (values) => {
                submitReview(frm, reviewName, values.review || "", "approve");
                dialog.hide();
            },
            secondary_action_label: __("Reject"),
            secondary_action: (values) => {
                submitReview(frm, reviewName, values.review || "", "reject");
                dialog.hide();
            }
        });
        
        dialog.show();
    }
});
