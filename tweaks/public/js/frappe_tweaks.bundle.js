


function apply_global_script(){
    frappe.call({
        method: "tweaks.custom.doctype.client_script.get_global_script",
        callback: function (response) {
			try {
				new Function(response.message)();
			} catch (e) {
				frappe.msgprint({
					title: __("Error in Global Client Script"),
					indicator: "orange",
					message: '<pre class="small"><code>' + e.stack + "</code></pre>",
				});
			}
        }
    })
}

apply_global_script()