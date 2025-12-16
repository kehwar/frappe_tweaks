// Copyright (c) 2025, and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sync Job Type', {
	refresh(frm) {
		// Show warning if module doesn't exist yet
		if (frm.doc.is_standard === 'Yes' && !frm.is_new()) {
			frappe.call({
				method: 'tweaks.utils.sync_job.check_sync_job_module_exists',
				args: {
					module: frm.doc.module,
					name: frm.doc.name
				},
				callback(r) {
					if (!r.message) {
						frm.dashboard.add_comment(
							__('Sync job module has not been created yet. Save the document to generate boilerplate files.'),
							'blue',
							true
						);
					}
				}
			});
		}
	}
});
