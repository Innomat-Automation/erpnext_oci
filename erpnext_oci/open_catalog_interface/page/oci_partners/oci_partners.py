@frappe.whitelist()
def get_partner_list():
	try:
		return frappe.get_all("OCI Partners", fields = ["Name","Username","Password","Url","AdditionalData"])
	except:
		return 'Error'
