// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["Report Snapshot Viewer"] = {
	"filters": [
		{
			"fieldname": "snapshot_file",
			"label": __("Snapshot File"),
			"fieldtype": "Link",
			"options": "File",
			"reqd": 1,
			"get_query": function() {
				return {
					"filters": {
						"is_folder": 0,
						"file_type": "JSON"
					}
				};
			}
		},
		{
			"fieldname": "column_header_mode",
			"label": __("Column Headers"),
			"fieldtype": "Select",
			"options": ["Fieldname", "Label"],
			"default": "Fieldname"
		},
		{
			"fieldname": "query",
			"label": __("Query"),
			"fieldtype": "Small Text",
			"reqd": 0,
			"description": __("DuckDB WHERE clause applied to table 'dataset' (example: qty > 10 AND status = 'Open')")
		},
	]
};
