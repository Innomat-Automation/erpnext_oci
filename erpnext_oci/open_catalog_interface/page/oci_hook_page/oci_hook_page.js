frappe.pages['oci-hook-page'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'OCI Hook Page',
		single_column: true
	});
}