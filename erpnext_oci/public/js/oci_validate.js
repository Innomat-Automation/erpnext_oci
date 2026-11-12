frappe.provide('erpnext_oci');

erpnext_oci.show_price_query = function(supplier) {
	function clear_result() {
		if (dialog) dialog.fields_dict.result.$wrapper.empty();
	}

	function update_product() {
		if (!dialog) return;
		clear_result();
		dialog.set_value('product_id', '');
		var item_code = dialog.get_value('item_code');
		var selected_supplier = dialog.get_value('supplier');
		if (!item_code || !selected_supplier) return;
		frappe.call({
			method: 'frappe.client.get',
			args: { doctype: 'Item', name: item_code },
			callback: function(response) {
				if (!response.message || dialog.get_value('item_code') !== item_code ||
					dialog.get_value('supplier') !== selected_supplier) return;
				var supplier_item = (response.message.supplier_items || []).find(function(row) {
					return row.supplier === selected_supplier;
				});
				if (supplier_item) dialog.set_value('product_id', supplier_item.supplier_part_no || '');
			}
		});
	}

	var dialog = new frappe.ui.Dialog({
		title: __('Price Query'),
		fields: [
			{ fieldname: 'supplier', fieldtype: 'Link', options: 'Supplier', label: __('Supplier'),
				reqd: 1, onchange: update_product },
			{ fieldname: 'item_code', fieldtype: 'Link', options: 'Item', label: __('Item'),
				onchange: update_product },
			{ fieldname: 'product_id', fieldtype: 'Data', label: __('Supplier Article Number'),
				reqd: 1, onchange: clear_result },
			{ fieldname: 'quantity', fieldtype: 'Float', label: __('Quantity'),
				reqd: 1, default: 1, onchange: clear_result },
			{ fieldname: 'result', fieldtype: 'HTML' }
		],
		primary_action_label: __('Query Price'),
		primary_action: function(values) {
			clear_result();
			frappe.call({
				method: 'erpnext_oci.open_catalog_interface.validation.validate_item',
				args: {
					supplier: values.supplier,
					product_id: values.product_id,
					quantity: values.quantity,
					hook_url: window.location.protocol + '//' + window.location.host +
						'/api/method/erpnext_oci.open_catalog_interface.utils.create_hock_page'
				},
				btn: dialog.get_primary_btn(),
				freeze: true,
				freeze_message: __('Querying price...'),
				callback: function(response) {
					if (!response.message) return;
					var container = $('<div class="table-responsive"></div>');
					var table = $('<table class="table table-bordered"></table>').appendTo(container);
					var heading = $('<tr></tr>').appendTo($('<thead></thead>').appendTo(table));
					['Supplier Article Number', 'Description', 'Price', 'Currency', 'Price Unit', 'UOM'].forEach(function(label) {
						$('<th></th>').text(__(label)).appendTo(heading);
					});
					var body = $('<tbody></tbody>').appendTo(table);
					response.message.prices.forEach(function(price) {
						var row = $('<tr></tr>').appendTo(body);
						[price.product_id || values.product_id, price.description, price.price,
							price.currency, price.price_unit, price.unit].forEach(function(value) {
							$('<td></td>').text(value || '').appendTo(row);
						});
					});
					dialog.fields_dict.result.$wrapper.empty().append(container);
				}
			});
		}
	});
	if (supplier) dialog.set_value('supplier', supplier);
	dialog.show();
};