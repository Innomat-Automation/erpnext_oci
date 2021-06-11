// Copyright (c) 2021, Asprotec AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('OCI Basket', {
	refresh: function(frm) {
		// render basket List
		if(frm.fields_dict['display']) {
			$(frm.fields_dict['display'].wrapper)
				.html(frappe.render_template("oci_basket",
					frm.doc.__onload));
		
			frappe.call({
				method: 'erpnext_oci.open_catalog_interface.utils.get_basket_data',
				args: {"cdn": frm.doc},
				callback: function(r) {
					if (r.message != 'Error') {
						show_table(r.message);
						frm.set_df_property("display","hidden",false);
					} else {
						console.log("fehler beim parsen");
					}
				}
			});
		}
		frm.add_custom_button(__("Erstelle alle Artikel"), function() {
			frappe.call({
				method: 'erpnext_oci.open_catalog_interface.utils.create_items',
				args: {"cdn": frm.doc},
				callback: function(r) {
					
				}
			});
		});
	}
});


function show_table(data) {
	var output = [];
	console.log(data);
	console.log(data.fields[0])
	// create header
	output.push('<thead>');
	output.push('<tr>');
   	for(var i = 0; i < data["fields"].length ;i++){
	   	output.push('<th>' + data["fields"][i].title + '</td>');
	}
	output.push('</tr>');
	output.push('</thead>');
	// create lines
	output.push('<tbody>');
	for(var i = 0; i < data.values.length ;i++){
		output.push('<tr>');
		for(var z = 0; z < data.fields.length ;z++){
			output.push('<td>' + data.values[i][data.fields[z].title] + '</td>');
		}
		output.push('</tr>');
	}
	output.push('</tbody>');
  	console.log(output)
	document.getElementById('table_body').innerHTML = document.getElementById('table_body').innerHTML + output.join('');
}
