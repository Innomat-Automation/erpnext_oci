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
		var passworddata = "";
		var additional = "";
		if(data[i].Password != null && data[i].Password != 'None')
		{
			passworddata = '<input type="hidden" name="Password" value="' + data[i].Password + '">';
		}
		if(data[i].AdditionalData != null)
		{
			adddata = data[i].AdditionalData.split(";");
			for(e = 0; e < adddata.length;e++)
			{
				value = adddata[e].split("=");
				if(value.length = 2) additional = additional + '<input type="hidden" name="' + value[0] + '" value="' + value[1] + '">';
			}
		}
	   	output.push('<td><form action="' + data[i].Url + '" method="' + data[i].Type + '" target="_blank">' + additional  + '<input type="hidden" name="USERNAME" value="' + data[i].Username + '">' + passworddata +'<input type="hidden" name="HOOK_URL" value="' + location.protocol + '//' + location.hostname + '/api/method/erpnext_oci.open_catalog_interface.utils.create_hock_page"><input type="hidden" name="~caller" value="' + data[i].Name + '"><input type="submit" value="Gehe zu Webshop"></form></td>');
		output.push('</tr>');
	}
  	
	document.getElementById('table_body').innerHTML = document.getElementById('table_body').innerHTML + output.join('');

}
