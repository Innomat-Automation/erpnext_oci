import frappe
from frappe import throw, _

@frappe.whitelist()
def get_partner_list():
	try:
		return frappe.get_all("OCI Partners", fields = ["Name","Username","Password","Url","Type","sapref","AdditionalData"])
	except:
		return 'Error'


