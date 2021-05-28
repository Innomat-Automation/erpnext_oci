frappe.pages['oci-partners'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'OCI Partners',
		single_column: true
	});

        frappe.oci_partners.make(page);
        frappe.oci_partners.run();
        frappe.oci_partners.show_data();
}

frappe.oci_partners = {
        start: 0,
        make: function(page) {
			    var me = frappe.oci_partners;     
                me.page = page;
                me.body = $('<div></div>').appendTo(me.page.main);
                var data = "";
                $(frappe.render_template('oci_partners', data)).appendTo(me.body);
        },
        run: function() {
        },
        show_data: function(){
		frappe.call({
			method: 'erpnext_oci.open_catalog_interface.page.oci_partners.oci_partners.get_partner_list',
			args: {},
			callback: function(r) {
				if (r.message != 'Error') {
					console.log("daten geparst:");
					console.log(r.message);
					show_table(r.message);
				} else {
					console.log("fehler beim parsen");
				}
			}
		});

	}
}

function show_table(data) {
	var output = [];
	console.log("Table");
	console.log(data);
    for(var i = 0; i < data.length ;i++){
		console.log(data[i]);
		output.push('<tr>');
	    output.push('<td>' + data[i].Name + '</td>');
	    output.push('<td><a href=' + data[i].Url + '?' + data[i].AdditionalData + '&Username=' + data[i].Username + '&Password=' + data[i].Password + '&HOOK_URL=http://192.168.80.31>Gehe zu Webshop</a></td>');
		output.push('</tr>');
	}
  	
	document.getElementById('table_body').innerHTML = document.getElementById('table_body').innerHTML + output.join('');
	
}
