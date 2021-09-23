import frappe
from frappe import throw, _

@frappe.whitelist()
def get_partner_list():
	try:
		data = frappe.get_all("OCI Partners", fields = ["Name","Username","Password","Url","Type","AdditionalData"])
		for item in data:
			doc = frappe.get_doc("OCI Partners",item.Name)
			if doc.password:
				item.Password = doc.get_password('Password')
		return data
	except:
		return 'Error'


