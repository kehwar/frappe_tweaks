import frappe


def execute():
	navbar_settings = frappe.get_single("Navbar Settings")

	if frappe.db.exists("Navbar Item", {"item_label": "Switch Language"}):
		return

	toggle_theme_index = None
	for i, item in enumerate(navbar_settings.settings_dropdown):
		if item.item_label == "Toggle Theme":
			toggle_theme_index = i
			break

	if toggle_theme_index is not None:
		insert_index = toggle_theme_index + 1
		for item in navbar_settings.settings_dropdown[insert_index:]:
			item.idx = item.idx + 1

		navbar_settings.append(
			"settings_dropdown",
			{
				"item_label": "Switch Language",
				"item_type": "Action",
				"action": "new tweaks.ui.LanguageSwitcher().show()",
				"is_standard": 1,
				"idx": insert_index + 1,
			},
		)
	else:
		navbar_settings.append(
			"settings_dropdown",
			{
				"item_label": "Switch Language",
				"item_type": "Action",
				"action": "new tweaks.ui.LanguageSwitcher().show()",
				"is_standard": 1,
			},
		)

	navbar_settings.save()
