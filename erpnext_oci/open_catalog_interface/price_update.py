from __future__ import unicode_literals

from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate

from erpnext_oci.open_catalog_interface.validation import request_supplier_validation


PRICE_CHECK_METHOD = "erpnext_oci.open_catalog_interface.price_update.run_supplier_price_check"
PRICE_CHECK_TIMEOUT = 86400
RETURN_METHOD = "erpnext_oci.open_catalog_interface.utils.create_hock_page"


@frappe.whitelist()
def enqueue_supplier_price_check(partner_name):
	frappe.only_for(("System Manager", "Purchase Manager", "Purchase Master Manager"))
	partner = frappe.get_doc("OCI Partners", partner_name)
	partner.check_permission("read")
	if not partner.get("validate"):
		frappe.throw(_("Enable Validate before starting a supplier price check."))
	job = frappe.enqueue(
		PRICE_CHECK_METHOD,
		queue="long",
		timeout=PRICE_CHECK_TIMEOUT,
		partner_name=partner.name,
	)
	return {"job_id": getattr(job, "id", None)}


def schedule_monthly_price_checks():
	partners = frappe.get_all(
		"OCI Partners",
		filters={"validate": 1, "auto_update_purchase_prices": 1},
		fields=["name"],
		limit_page_length=1000,
	)
	for partner in partners:
		try:
			frappe.enqueue(
				PRICE_CHECK_METHOD,
				queue="long",
				timeout=PRICE_CHECK_TIMEOUT,
				partner_name=partner.name,
			)
		except Exception as error:
			_log_partner_error(partner.name, error)


def run_supplier_price_check(partner_name):
	partner = frappe.get_doc("OCI Partners", partner_name)
	result = {"checked": 0, "updated": 0, "unchanged": 0, "errors": 0}
	try:
		price_list = _get_price_list(partner)
		price_list_data = frappe.db.get_value(
			"Price List", price_list, ["buying", "currency"], as_dict=True
		)
		if not price_list_data or not price_list_data.buying:
			raise ValueError("Price List {} is not an enabled buying list.".format(price_list))
		quantity = cint(partner.get("price_check_quantity") or 1)
		if quantity < 1:
			raise ValueError("Price Check Quantity must be at least 1.")
		hook_url = frappe.utils.get_url("/api/method/{}".format(RETURN_METHOD))
		items = frappe.get_all(
			"Item Supplier",
			filters={"supplier": partner.supplier},
			fields=["parent", "supplier_part_no"],
			order_by="parent asc",
			limit_page_length=100000,
		)
		if not items:
			raise ValueError("No Item Supplier records found for supplier {}.".format(partner.supplier))
	except Exception as error:
		_log_partner_error(partner_name, error)
		frappe.db.commit()
		result["errors"] += 1
		return result

	for supplier_item in items:
		item_code = supplier_item.parent
		supplier_part_no = supplier_item.supplier_part_no
		result["checked"] += 1
		try:
			if not supplier_part_no:
				raise ValueError("Supplier article number is missing.")
			price_result = request_supplier_validation(
				partner, supplier_part_no, quantity, hook_url
			)
			price = _select_price(price_result.get("prices") or [], supplier_part_no)
			currency = price.get("currency")
			if currency and currency != price_list_data.currency:
				raise ValueError(
					"Supplier returned currency {}; price list {} uses {}.".format(
						currency, price_list, price_list_data.currency
					)
				)
			new_rate = _to_decimal(price.get("price"))
			updated = _update_supplier_price(
				item_code, partner.supplier, price_list, quantity, new_rate
			)
			result["updated" if updated else "unchanged"] += 1
		except Exception as error:
			frappe.db.rollback()
			_log_item_error(partner, item_code, supplier_part_no, price_list, error)
			result["errors"] += 1
		finally:
			frappe.db.commit()
	return result


def _get_price_list(partner):
	price_lists = sorted(set(
		row.pricelist for row in partner.fields
		if row.fieldtype == "Item-Price" and row.pricelist
	))
	if len(price_lists) != 1:
		raise ValueError(
			"Configure exactly one Price List on an Item-Price field for OCI partner {}.".format(
				partner.name
			)
		)
	return price_lists[0]


def _select_price(prices, supplier_part_no):
	matching = [price for price in prices if price.get("product_id") == supplier_part_no]
	if matching:
		prices = matching
	elif any(price.get("product_id") for price in prices):
		raise ValueError("Supplier response does not match article {}.".format(supplier_part_no))
	if len(prices) != 1:
		raise ValueError("Supplier returned {} prices for article {}.".format(len(prices), supplier_part_no))
	return prices[0]


def _to_decimal(value):
	try:
		price = Decimal(str(value))
		if not price.is_finite() or price < 0:
			raise ValueError
	except (InvalidOperation, ValueError):
		raise ValueError("Supplier returned an invalid price: {}.".format(value))
	return price


def _update_supplier_price(item_code, supplier, price_list, min_qty, new_rate, today=None):
	today = getdate(today or nowdate())
	rows = frappe.get_all(
		"Item Price",
		filters={"item_code": item_code, "price_list": price_list, "supplier": supplier},
		fields=["name", "price_list_rate", "min_qty", "uom", "packing_unit", "valid_from", "valid_upto"],
		limit_page_length=10000,
	)
	rows = [row for row in rows if not row.uom and cint(row.min_qty) == min_qty and not cint(row.packing_unit)]
	current = [row for row in rows if _is_effective(row, today)]
	if len(current) > 1:
		raise ValueError("Multiple active supplier Item Prices exist for this article, price list and quantity.")
	if current:
		old_rate = _to_decimal(current[0].price_list_rate)
		if old_rate == new_rate:
			return False
		old_doc = frappe.get_doc("Item Price", current[0].name)
		if old_doc.valid_from and getdate(old_doc.valid_from) == today:
			old_doc.price_list_rate = float(new_rate)
			old_doc.save(ignore_permissions=True)
			return True
		old_doc.valid_upto = add_days(today, -1)
		old_doc.save(ignore_permissions=True)

	future_dates = [
		getdate(row.valid_from) for row in rows
		if row.valid_from and getdate(row.valid_from) > today
	]
	valid_upto = add_days(min(future_dates), -1) if future_dates else None
	new_doc = frappe.get_doc({
		"doctype": "Item Price",
		"item_code": item_code,
		"price_list": price_list,
		"supplier": supplier,
		"price_list_rate": float(new_rate),
		"min_qty": min_qty,
		"valid_from": today,
		"valid_upto": valid_upto,
	})
	new_doc.insert(ignore_permissions=True)
	return True


def _is_effective(row, today):
	valid_from = getdate(row.valid_from) if row.valid_from else None
	valid_upto = getdate(row.valid_upto) if row.valid_upto else None
	return (not valid_from or valid_from <= today) and (not valid_upto or valid_upto >= today)


def _log_item_error(partner, item_code, supplier_part_no, price_list, error):
	message = (
		"Supplier: {0}\nItem: {1}\nSupplier article number: {2}\n"
		"Price List: {3}\nError: {4}"
	).format(partner.supplier, item_code, supplier_part_no or "", price_list, error)
	frappe.log_error(message=message, title="OCI Price Check Failed: {}".format(item_code))


def _log_partner_error(partner_name, error):
	frappe.log_error(
		message="OCI Partner: {}\nError: {}".format(partner_name, error),
		title="OCI Price Check Configuration Failed: {}".format(partner_name),
	)