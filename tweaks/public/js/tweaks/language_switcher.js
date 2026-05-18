frappe.provide("tweaks.ui");

tweaks.ui.LanguageSwitcher = class LanguageSwitcher {
	constructor() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Switch Language"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "language",
					label: __("Language"),
					options: "Language",
					default: frappe.boot.lang,
					get_query: () => ({ filters: { enabled: 1 } }),
				},
			],
			primary_action_label: __("Switch"),
			primary_action: ({ language }) => {
				if (!language) return;
				this.dialog.hide();
				frappe.show_alert(__("Switching Language..."), 5);
				frappe.xcall("tweaks.api.language.switch_language", { language }).then(() => {
					window.location.reload();
				});
			},
		});
	}

	show() {
		this.dialog.show();
	}
};
