frappe.ui.form.on('Quotation', {
    refresh(frm) {
        if (frm.doc.docstatus == 0) {
            // button to create sales invoice
            frm.add_custom_button(__("OCI Import"), function() {
                oci_import(frm);
            });
        }
    }
});

function oci_import(frm) {
    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'oci_basket', 'fieldtype': 'Link', 'label': __('OCI Basket'), 'options': 'OCI Basket', 'reqd': 1}
        ],
        primary_action: function() {
            d.hide();
            var values = d.get_values();
            frappe.call({
                method: 'erpnext_oci.open_catalog_interface.utils.get_basket_items',
                args: {
                    basket: values.oci_basket
                },
                "callback": function(response) {
                    console.log(response.message);
                    for (var i = 0; i < response.message.length; i++) {
                        var child = cur_frm.add_child('items');
                        console.log(response.message[i]);
                        frappe.model.set_value(child.doctype, child.name, 'item_code', response.message[i].item_code);
                        frappe.model.set_value(child.doctype, child.name, 'qty', response.message[i].quantity);
                    }
                    cur_frm.refresh_field('items');
                    // clean up uom and rates
                    for (var i = 0; i < frm.doc.items.length; i++) {
                        if (!frm.doc.items[i].uom) {
                            frappe.call({
                                "method": "frappe.client.get",
                                "args": {
                                    "doctype": "Item",
                                    "name": frm.doc.items[i].item_code
                                    },
                                "async": false,
                                "callback": function(response) {
                                    var item = response.message;
                                    frappe.model.set_value(frm.doc.items[i].doctype, frm.doc.items[i].name, 'uom', item.stock_uom);
                                }
                            });
                        }
                    }
                }
            });
        },
        primary_action_label: __('OK'),
        title: __('OCI Import')
    });
    d.show();
}