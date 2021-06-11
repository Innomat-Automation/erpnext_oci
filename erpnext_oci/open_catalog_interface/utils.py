
# Copyright (c) 2019-2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from datetime import date
from frappe import _



@frappe.whitelist(allow_guest=True)
def create_hock_page():
	# Check has a message 
	data = frappe.form_dict;

	if(not ('~caller' in data.keys())):
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/desk#"
		return
	
	basket = frappe.get_doc({
                "doctype": "OCI Basket",
				"oci_partner" : data['~caller'],
				"date" : date.today(),
				"data" : json.dumps(json.loads(str(data).replace("'","\"")))
            })
	basket.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/desk#List/OCI%20Basket/List"



@frappe.whitelist()
def get_basket_data(cdn):
	doc = json.loads(cdn)
	partner = frappe.get_doc("OCI Partners",doc["oci_partner"])
	fields = []
	item_code = ""
	# create fields for display and header
	for value in partner.fields:
		if(value.show_in_table):
			fields.append(value)
		if(value.fieldtype == "Item-Field" and value.fieldname == "item_code"):
			item_code = value.returnfield

	data = json.loads(doc['data'])

	i = 0 
	values = []
	while True:
		if (fields[0].returnfield.replace("%",str(i+1))) not in data:
			break
		
		details = {}
		# add field infromations
		for z in range(len(fields)):
			details[fields[z].title] = ""
			if (fields[z].returnfield.replace("%",str(i+1)))in data:
				details[fields[z].title] = data[fields[z].returnfield.replace("%",str(i+1))]
		# check item exist
		exist = True;
		if item_code != "" and ((item_code.replace("%",str(i+1))) in data):
			exist = frappe.db.exists("Item",data[item_code.replace("%",str(i+1))])
		details["exist"] = exist

		values.append(details)
		i = i+1		

	response = {}
	response["fields"] = fields
	response["values"] = values

	return response

@frappe.whitelist()
def get_basket_items(basket):
	oci_basket = frappe.get_doc("OCI Basket", basket)
	partner = frappe.get_doc("OCI Partners",oci_basket.oci_partner)

	basket_quantity = "";
	item_code = "";

	for value in partner.fields:
		if(value.fieldtype == "Basket-Quantity"):
			basket_quantity = value.returnfield
		if(value.fieldtype == "Item-Field" and value.fieldname == "item_code"):
			item_code = value.returnfield
	
	data = json.loads(oci_basket.data)
	result = [];
	i = 0
	while True:
		if (item_code.replace("%",str(i+1))) not in data:
			break
		
		item_codename = "";
		item_quantity = 1;
		#parse data
		if item_code != "" and ((item_code.replace("%",str(i+1))) in data):
			item_codename = data[item_code.replace("%",str(i+1))]
		if basket_quantity != "" and ((basket_quantity.replace("%",str(i+1))) in data):
			item_quantity = data[basket_quantity.replace("%",str(i+1))]



		result.append({"item_code" : item_codename, "quantity" : item_quantity})
		i = i+1	

	return result


@frappe.whitelist()
def create_items(cdn):
	doc = json.loads(cdn)
	partner = frappe.get_doc("OCI Partners",doc["oci_partner"])
	supplier = partner.supplier
	itemfields = []
	pricefields = []
	uomfields = []
	item_code = ""
	result = []
	# fiend fields
	for value in partner.fields:
		if(value.fieldtype == "Item-Field" and value.fieldname != "item_code" and value.fieldname):
			itemfields.append(value)
		if(value.fieldtype == "Item-Price"):
			pricefields.append(value)
		if(value.fieldtype == "Item-UOM"):
			uomfields.append(value)
		if(value.fieldtype == "Item-Field" and value.fieldname == "item_code"):
			item_code = value.returnfield


	data = json.loads(doc['data'])

	i = 0 
	while True:
		if (itemfields[0].returnfield.replace("%",str(i+1))) not in data:
			break
		
		item_codename = "";
		#parse data
		exist = True;
		if item_code != "" and ((item_code.replace("%",str(i+1))) in data):
			item_codename = data[item_code.replace("%",str(i+1))]
			exist = frappe.db.exists("Item",item_codename)
		
		if exist:
			i = i+1
			continue

		itemdata = {}
		# add field infromations
		for z in range(len(itemfields)):
			itemdata[itemfields[z].fieldname] = itemfields[z].default
			if (itemfields[z].returnfield.replace("%",str(i+1)))in data:
				itemdata[itemfields[z].fieldname] = data[itemfields[z].returnfield.replace("%",str(i+1))]

		# add uom infromations
		uomdata = {}
		for z in range(len(uomfields)):
			uomdata[uomfields[z].fieldname] = itemfields[z].default
			if (uomfields[z].returnfield.replace("%",str(i+1)))in data:
				uomdata[uomfields[z].fieldname] = data[uomfields[z].returnfield.replace("%",str(i+1))]

		# add price infromations
		pricedata = [len(pricefields)]
		for z in range(len(pricefields)):
			pricedata[z] = {}
			pricedata[z]['field'] = [pricefields[z].fieldname]
			if (pricefields[z].pricelist != None):
				pricedata[z]['pricelist'] = pricefields[z].pricelist
			if (pricefields[z].returnfield.replace("%",str(i+1)))in data:
				pricedata[z]['price'] = data[pricefields[z].returnfield.replace("%",str(i+1))]


		result.append(create_item(item_codename,itemdata,uomdata,pricedata,supplier,item_codename,partner.item_defaults))
		i = i+1	

	return "Items added: <br/>" + "<br/>".join(result)

def create_item(item_codename,itemdata,uomdata,pricedata,supplier,supplier_part_no,defaults):
    
	docdata = {}
	docdata["doctype"] = "Item"
	docdata["item_code"] = item_codename
	docdata["show_in_website"] = 1
	docdata["is_sales_item"] = 1
	docdata["is_purchase_item"] = 1
	docdata["is_stock_item"] = 1
	for key,field in itemdata.items():
		docdata[key] = field
	for key,field in uomdata.items():
		docdata[key] = field
	docdata["item_defaults"] = defaults
	docdata["supplier_items"] = [{
								"supplier" : supplier,
								"supplier_part_no" : supplier_part_no
								}]

	new_item = frappe.get_doc(docdata)
	new_item.insert()

	for price in pricedata:
		item_price = frappe.get_doc({
			"doctype": "Item Price",
			"price_list": price["pricelist"],
			"item_code": new_item.item_code,
			"price_list_rate": price["price"]
		}).insert()

	return item_codename


