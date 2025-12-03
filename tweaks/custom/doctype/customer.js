frappe.provide("frappe.ui.form");

frappe.ui.form.SUNATCustomerQuickEntryForm = class SUNATCustomerQuickEntryForm extends (frappe.ui.form.QuickEntryForm) {
    /**
     * Set up the form, initializing with a term if coming from a link.
     */
    setup() {
        if (frappe._from_link) {
            // Capture the input value from the link
            this.term = frappe._from_link.input.value
        }
        return super.setup()
    }

    /**
     * Set meta and mandatory fields, filtering to only include 'tax_id'.
     */
    set_meta_and_mandatory_fields() {
        super.set_meta_and_mandatory_fields()

        // Filter mandatory fields to include only 'tax_id'
        this.mandatory = this.mandatory.filter((f) => f.fieldname === 'tax_id')
    }

    /**
     * Register the primary action for the dialog, which searches on SUNAT.
     */
    register_primary_action() {
        const me = this

        // Set the primary action of the dialog to search on SUNAT
        this.dialog.set_primary_action(__('Search on SUNAT'), () => {
            if (me.dialog.working) {
                return
            }
            const data = me.dialog.get_values()

            if (data) {
                me.dialog.working = true

                // Insert the data and clear messages upon completion
                me.insert().then(() => {
                    me.dialog.clear_message()
                })
            }
        })
    }

    /**
     * Set default values for dialog fields.
     */
    set_defaults() {
        // Pre-fill the 'tax_id' input field with the captured term
        this.dialog.fields_dict.tax_id.set_input(this.term)
    }

    /**
     * Display an error message.
     * @param {string} title - The title of the error message.
     * @param {Error} exc - The exception object.
     */
    displayError(title, exc) {
        frappe.msgprint({
            indicator: 'red',
            title,
            message: __(exc.exception),
        })
    }

    /**
     * Insert a new customer by calling the backend API and handle the response.
     * @returns {Promise<object>} The resulting document.
     */
    insert() {
        const me = this
        return new Promise((resolve) => {
            me.update_doc()

            me.validateCustomerId(resolve)
        })
    }

    /**
     * Validate the customer's ID by calling the backend.
     * @param {Function} resolve - The function to call upon resolving the promise.
     */
    validateCustomerId(resolve) {
        const me = this
        frappe.call({
            method: 'tweaks.tweaks.doctype.peru_api_com.peru_api_com.get_rut',
            args: { rut: me.dialog.doc.tax_id, raise_exception: 0 },
            error: (exc) => me.displayError(__('Error while searching RUC/DNI on SUNAT'), exc),
            always() {
                // Reset the dialog working state and resolve the promise with doc
                me.dialog.working = false
                resolve(me.dialog.doc)
            },
            freeze: true,
            freeze_message: __('Searching RUC/DNI on SUNAT...'),
            callback({ message }) {

                if (!message) {
                    frappe.msgprint({
                        indicator: 'red',
                        title: __('Error'),
                        message: __("RUC/DNI '{0}' not found on SUNAT", [me.dialog.doc.tax_id]),
                    })
                    return
                }

                frappe.confirm(
                    __('Create customer {0} ?', [message.razon_social || message.cliente]),
                    () => me.createCustomer(message.ruc || message.dni),
                )
            },
        })
    }

    /**
     * Create a new customer by calling the backend.
     * @param {string} customerId - The ID of the customer to create.
     */
    createCustomer(customerId) {
        const me = this
        frappe.call({
            method: 'tweaks.tweaks.doctype.peru_api_com.peru_api_com.create_customer',
            args: { rut: customerId },
            freeze: true,
            freeze_message: __('Creating customer...'),
            error: (exc) => me.displayError(__('Error while searching RUC/DNI on SUNAT'), exc),
            callback(response) {
                me.dialog.hide()

                // Clear the old document and update with the new one
                frappe.model.clear_doc(me.dialog.doc.doctype, me.dialog.doc.name)
                me.dialog.doc = response.message

                if (frappe._from_link) {
                    frappe.ui.form.update_calling_link(me.dialog.doc)
                }
                else if (me.after_insert) {
                    me.after_insert(me.dialog.doc)
                }
                else if (frappe.get_route()?.[0] === 'List') {
                    cur_list.refresh()
                    frappe.show_alert({ message: __("{0} created successfully", [__('Customer')]), indicator: 'green' })
                }
                else {
                    me.open_form_if_not_list()
                }
            },
        })
    }
}

frappe.ui.form.CustomerQuickEntryForm = frappe.ui.form.SUNATCustomerQuickEntryForm