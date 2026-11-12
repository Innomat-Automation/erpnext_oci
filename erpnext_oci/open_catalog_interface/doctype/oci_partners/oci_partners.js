// Copyright (c) 2021, Asprotec AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('OCI Partners', {
	refresh: function(frm) {
		if (!frm.is_new() && frm.doc.validate) {
			frm.add_custom_button(__('Price Query'), function() {
				if (frm.is_dirty()) {
					frappe.msgprint(__('Please save the OCI partner before querying prices.'));
					return;
				}
				frappe.require('/assets/erpnext_oci/js/oci_validate.js', function() {
					erpnext_oci.show_price_query(frm.doc.supplier);
				});
			});
			frm.add_custom_button(__('Check Purchase Prices'), function() {
				frappe.call({
					method: 'erpnext_oci.open_catalog_interface.price_update.enqueue_supplier_price_check',
					args: { partner_name: frm.doc.name },
					freeze: true,
					freeze_message: __('Queueing supplier price check...'),
					callback: function(response) {
						if (response.message) {
							frappe.msgprint(__('Price check queued. Review Error Log for item failures.'));
						}
					}
				});
			});
		}
	}
});
