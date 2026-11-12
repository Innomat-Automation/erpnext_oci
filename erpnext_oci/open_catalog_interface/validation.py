from __future__ import unicode_literals

from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlparse

import frappe
import requests
from bs4 import BeautifulSoup
from frappe import _


@frappe.whitelist()
def validate_item(supplier, product_id, quantity=1, hook_url=None):
	frappe.only_for(("Purchase User", "Purchase Manager", "System Manager"))
	if not isinstance(supplier, str) or not supplier.strip():
		frappe.throw(_("Please select a supplier."))
	if not isinstance(product_id, str) or not product_id.strip():
		frappe.throw(_("Please enter a supplier article number."))
	try:
		amount = Decimal(str(quantity))
		if not amount.is_finite() or amount <= 0:
			raise ValueError
	except (InvalidOperation, ValueError):
		frappe.throw(_("Quantity must be a positive number."))

	partner_name = frappe.db.get_value("OCI Partners", {"supplier": supplier}, "name")
	if not partner_name:
		frappe.throw(_("No OCI partner is configured for this supplier."))
	partner = frappe.get_doc("OCI Partners", partner_name)
	frappe.get_doc("Supplier", supplier).check_permission("read")
	if not partner.get("validate"):
		frappe.throw(_("Validate is not enabled for this OCI partner."))
	return request_supplier_validation(partner, product_id, quantity, hook_url)


def request_supplier_validation(partner, product_id, quantity=1, hook_url=None):
	try:
		amount = Decimal(str(quantity))
		if not amount.is_finite() or amount <= 0:
			raise ValueError
	except (InvalidOperation, ValueError):
		frappe.throw(_("Quantity must be a positive number."))
	if urlparse(partner.url).scheme not in ("http", "https") or partner.type not in ("GET", "POST"):
		frappe.throw(_("Please configure a valid OCI URL and request type."))
	hook = urlparse(hook_url or "")
	if hook.scheme not in ("http", "https") or not hook.netloc:
		frappe.throw(_("Please provide a valid OCI return URL."))

	parameters = {}
	for entry in (partner.additionaldata or "").split(";"):
		if not entry.strip():
			continue
		key, separator, value = entry.partition("=")
		if not separator or not key.strip():
			frappe.throw(_("Invalid OCI additional data. Use key=value; entries."))
		parameters[key.strip()] = value
	parameters[partner.userfield] = partner.username
	if partner.password:
		parameters[partner.passfield] = partner.get_password("password")
	quantity_field = partner.get("validate_quantity_field") or "QUANTITY"
	for key in ("FUNCTION", "PRODUCTID", "QUANTITY", "Quantity", "HOOK_URL", "~caller"):
		parameters.pop(key, None)
	parameters["FUNCTION"] = "VALIDATE"
	parameters["PRODUCTID"] = product_id.strip()
	parameters[quantity_field] = str(amount)
	parameters["HOOK_URL"] = hook_url
	parameters["~caller"] = partner.name
	supplier_origin = "{}://{}".format(urlparse(partner.url).scheme, urlparse(partner.url).netloc)
	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.0.0",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		"Accept-Language": "de,de-DE;q=0.9,en;q=0.8",
		"Origin": supplier_origin,
		"Referer": supplier_origin + "/",
	}
	error_message = None
	try:
		response = requests.request(
			partner.type, partner.url,
			params=parameters if partner.type == "GET" else None,
			data=parameters if partner.type == "POST" else None,
			headers=headers,
			timeout=30,
		)
		response.raise_for_status()
	except requests.exceptions.SSLError:
		error_message = _("OCI TLS certificate verification failed. Check the supplier certificate and the server CA certificates.")
	except requests.exceptions.ProxyError:
		error_message = _("The OCI proxy connection failed. Check the ERP server proxy settings.")
	except requests.Timeout:
		error_message = _("The OCI supplier did not respond within the connection or read timeout (30 seconds).")
	except requests.HTTPError as error:
		if error.response is not None:
			error_message = _("The OCI supplier returned HTTP {0}. Check the OCI URL, GET/POST request type and supplier access permissions.").format(error.response.status_code)
		else:
			error_message = _("The OCI supplier returned an HTTP error.")
	except requests.ConnectionError:
		error_message = _("The ERP server cannot connect to the OCI supplier. Check DNS, network access and the OCI URL.")
	except requests.RequestException:
		error_message = _("The OCI price query failed. Please check the partner settings or try again later.")
	if error_message:
		frappe.throw(error_message)
	return parse_validation_response(response.text, partner)


def parse_validation_response(body, partner):
	soup = BeautifulSoup(body, "html.parser")
	values = {field.get("name"): field.get("value", "")
		for field in soup.find_all("input", attrs={"name": True})}
	if not values:
		values = dict(parse_qsl(body.strip(), keep_blank_values=True))
	if values.get("ERROR", "").strip():
		message = frappe.utils.escape_html(values["ERROR"].strip())
		frappe.throw(_("The supplier returned an OCI error: {0}").format(message))
	price_fields = [field for field in partner.get("fields", []) if field.fieldtype == "Item-Price"]
	prices = []
	for key, value in values.items():
		prefix = "NEW_ITEM-PRICE["
		if key.startswith(prefix) and key.endswith("]"):
			index = key[len(prefix):-1]
			if index.isdigit() and value.strip():
				prices.append({
					"product_id": values.get("NEW_ITEM-EXT_PRODUCT_ID[{}]".format(index), values.get("NEW_ITEM-VENDORMAT[{}]".format(index), "")),
					"description": values.get("NEW_ITEM-DESCRIPTION[{}]".format(index), ""),
					"price": value,
					"currency": values.get("NEW_ITEM-CURRENCY[{}]".format(index), ""),
					"price_unit": values.get("NEW_ITEM-PRICEUNIT[{}]".format(index), "1"),
					"unit": values.get("NEW_ITEM-UNIT[{}]".format(index), ""),
				})
	for field in price_fields:
		key = (field.returnfield or "").replace("%", "1")
		if key and not key.startswith("NEW_ITEM-PRICE[") and values.get(key, "").strip():
			prices.append({"description": field.title or field.pricelist or key, "price": values[key],
				"currency": values.get("NEW_ITEM-CURRENCY[1]", ""),
				"price_unit": values.get("NEW_ITEM-PRICEUNIT[1]", "1"),
				"unit": values.get("NEW_ITEM-UNIT[1]", "")})
	if not prices:
		frappe.throw(_("The supplier returned no OCI price. Check the article number and the supplier's VALIDATE support."))
	return {"supplier": partner.supplier, "prices": prices}