# -*- coding: utf-8 -*-
# Copyright (c) 2021, Asprotec AG and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import Mock, patch

import frappe
import requests
from erpnext_oci.open_catalog_interface.validation import validate_item, parse_validation_response
from erpnext_oci.open_catalog_interface.price_update import (
	_update_supplier_price,
	_select_price,
	enqueue_supplier_price_check,
	run_supplier_price_check,
	schedule_monthly_price_checks,
)

class TestOCIPartners(unittest.TestCase):
	def setUp(self):
		self.partner = frappe._dict({
			"name": "Test Partner", "supplier": "Test Supplier", "validate": 1, "type": "POST",
			"url": "https://catalog.example/oci", "userfield": "USERNAME",
			"username": "test-user", "passfield": "PASSWORD", "password": "hidden",
			"additionaldata": "SITEID=CH;", "fields": [],
			"check_permission": Mock(), "get_password": Mock(return_value="secret"),
		})
		self.response = '<input name="NEW_ITEM-PRICE[1]" value="12.50"><input name="NEW_ITEM-CURRENCY[1]" value="CHF">'
		request_patch = patch("erpnext_oci.open_catalog_interface.validation.requests.request")
		self.request = request_patch.start()
		self.addCleanup(request_patch.stop)
		permission_patch = patch("frappe.only_for")
		self.authorize = permission_patch.start()
		self.addCleanup(permission_patch.stop)

	def throw(self, message):
		raise ValueError(message)

	def call_validation(self, **kwargs):
		with patch("frappe.db", Mock(get_value=Mock(return_value="Test Partner"))), \
			patch("frappe.get_doc", return_value=self.partner), \
			patch("frappe.throw", side_effect=self.throw):
			self.request.return_value.text = self.response
			kwargs.setdefault("hook_url", "https://erp.example/api/method/erpnext_oci.open_catalog_interface.utils.create_hock_page")
			result = validate_item("Test Supplier", "A-123", **kwargs)
			return result, self.request

	def test_validate_request(self):
		result, request = self.call_validation(quantity="2.5")
		parameters = request.call_args[1]["data"]
		self.assertEqual(parameters["FUNCTION"], "VALIDATE")
		self.assertEqual(parameters["PRODUCTID"], "A-123")
		self.assertEqual(parameters["QUANTITY"], "2.5")
		self.assertEqual(parameters["SITEID"], "CH")
		self.assertEqual(parameters["PASSWORD"], "secret")
		self.assertEqual(parameters["HOOK_URL"], "https://erp.example/api/method/erpnext_oci.open_catalog_interface.utils.create_hock_page")
		self.assertEqual(parameters["~caller"], "Test Partner")
		self.assertEqual(list(parameters), ["SITEID", "USERNAME", "PASSWORD", "FUNCTION", "PRODUCTID", "QUANTITY", "HOOK_URL", "~caller"])
		headers = request.call_args[1]["headers"]
		self.assertEqual(headers["Origin"], "https://catalog.example")
		self.assertEqual(headers["Referer"], "https://catalog.example/")
		self.assertIn("Chrome/157.0.0.0", headers["User-Agent"])
		self.assertEqual(result["prices"][0]["price"], "12.50")
		self.partner.check_permission.assert_called_with("read")
		self.authorize.assert_called_with(("Purchase User", "Purchase Manager", "System Manager"))

	def test_configured_validate_quantity_field_and_order(self):
		self.partner.validate_quantity_field = "Quantity"
		self.call_validation(quantity=10)
		parameters = self.request.call_args[1]["data"]
		self.assertEqual(parameters["Quantity"], "10")
		self.assertNotIn("QUANTITY", parameters)
		self.assertEqual(list(parameters), ["SITEID", "USERNAME", "PASSWORD", "FUNCTION", "PRODUCTID", "Quantity", "HOOK_URL", "~caller"])

	def test_get_request(self):
		self.partner.type = "GET"
		result, request = self.call_validation()
		self.assertIsNone(request.call_args[1]["data"])
		self.assertEqual(request.call_args[1]["params"]["PRODUCTID"], "A-123")

	def test_disabled_validate_does_not_call_supplier(self):
		self.partner.validate = 0
		with self.assertRaisesRegex(ValueError, "not enabled"):
			self.call_validation()
		self.request.assert_not_called()

	def test_invalid_quantities(self):
		for quantity in ("0", "-1", "NaN", "Infinity", "bad"):
			with self.assertRaisesRegex(ValueError, "positive number"):
				self.call_validation(quantity=quantity)

	def test_html_and_encoded_response(self):
		for body in (self.response, "NEW_ITEM-PRICE%5B1%5D=12.50&NEW_ITEM-CURRENCY%5B1%5D=CHF"):
			result = parse_validation_response(body, self.partner)
			self.assertEqual(result["prices"][0]["currency"], "CHF")

	def test_empty_response_is_not_a_price(self):
		with patch("frappe.throw", side_effect=self.throw):
			with self.assertRaisesRegex(ValueError, "no OCI price"):
				parse_validation_response("<html>Login failed</html>", self.partner)

	def test_encoded_oci_error_is_reported(self):
		body = "%7Etarget=_top&%7Ecaller=CTLG&%7Eforcetarget=yes&%7EOkCode=ADDI&ERROR=The+requested+product+or+quantity+has+warnings+or+errors+that+must+be+resolved"
		with patch("frappe.throw", side_effect=self.throw):
			with self.assertRaisesRegex(ValueError, "requested product or quantity"):
				parse_validation_response(body, self.partner)

	def test_html_oci_error_is_escaped(self):
		body = '<input name="ERROR" value="&lt;script&gt;bad&lt;/script&gt;">'
		with patch("frappe.throw", side_effect=self.throw):
			with self.assertRaisesRegex(ValueError, "&lt;script&gt;bad&lt;/script&gt;"):
				parse_validation_response(body, self.partner)

	def test_permission_denied_does_not_call_supplier(self):
		self.authorize.side_effect = frappe.PermissionError
		with self.assertRaises(frappe.PermissionError):
			self.call_validation()
		self.request.assert_not_called()

	def test_supplier_permission_denied_does_not_call_supplier(self):
		self.partner.check_permission.side_effect = frappe.PermissionError
		with self.assertRaises(frappe.PermissionError):
			self.call_validation()
		self.request.assert_not_called()

	def test_connection_error_does_not_expose_credentials(self):
		self.request.side_effect = requests.RequestException("secret")
		with self.assertRaisesRegex(ValueError, "price query failed") as error:
			self.call_validation()
		self.assertNotIn("secret", str(error.exception))
		self.assertIsNone(error.exception.__context__)

	def test_network_errors_report_safe_reason(self):
		cases = (
			(requests.exceptions.SSLError, "TLS certificate"),
			(requests.exceptions.ProxyError, "proxy connection"),
			(requests.Timeout, "30 seconds"),
			(requests.ConnectionError, "cannot connect"),
		)
		for exception, message in cases:
			with self.subTest(exception=exception):
				self.request.side_effect = exception("https://catalog.example/?PASSWORD=secret")
				with self.assertRaisesRegex(ValueError, message) as error:
					self.call_validation()
				self.assertNotIn("secret", str(error.exception))
				self.assertIsNone(error.exception.__context__)

	def test_http_errors_report_status_without_credentials(self):
		for status in (401, 403, 404, 405, 429, 500):
			with self.subTest(status=status):
				response = requests.Response()
				response.status_code = status
				self.request.return_value.raise_for_status.side_effect = requests.HTTPError(
					"https://catalog.example/?PASSWORD=secret", response=response)
				with self.assertRaisesRegex(ValueError, "HTTP {}".format(status)) as error:
					self.call_validation()
				self.assertNotIn("secret", str(error.exception))
				self.assertIsNone(error.exception.__context__)

	def test_custom_price_mapping_and_price_unit(self):
		self.partner.fields = [frappe._dict({"fieldtype": "Item-Price", "returnfield": "NET[%]", "title": "Net"})]
		result = parse_validation_response('<input name="NET[1]" value="0"><input name="NEW_ITEM-PRICEUNIT[1]" value="100">', self.partner)
		self.assertEqual(result["prices"][0]["price"], "0")
		self.assertEqual(result["prices"][0]["price_unit"], "100")

	def test_price_selection_matches_supplier_article_number(self):
		prices = [
			{"product_id": "OTHER", "price": "1.00"},
			{"product_id": "SUP-1", "price": "2.00"},
		]
		self.assertEqual(_select_price(prices, "SUP-1")["price"], "2.00")

	def test_item_price_change_closes_old_and_starts_today(self):
		old_price = Mock(valid_from="2026-01-01", valid_upto=None, price_list_rate=10)
		new_price = Mock()
		new_document = {}
		def get_doc(*args):
			if isinstance(args[0], dict):
				new_document.update(args[0])
				return new_price
			return old_price
		with patch("erpnext_oci.open_catalog_interface.price_update.frappe.get_all", return_value=[frappe._dict({
			"name": "OLD", "price_list_rate": 10, "min_qty": 10, "uom": None,
			"packing_unit": 0, "valid_from": "2026-01-01", "valid_upto": None,
		})]), patch("erpnext_oci.open_catalog_interface.price_update.frappe.get_doc", side_effect=get_doc):
			updated = _update_supplier_price("ITEM-1", "SUP-1", "Standard-Kauf", 10, 12.5, today="2026-11-12")
		self.assertTrue(updated)
		self.assertEqual(str(old_price.valid_upto), "2026-11-11")
		old_price.save.assert_called_once_with(ignore_permissions=True)
		self.assertEqual(str(new_document["valid_from"]), "2026-11-12")
		self.assertEqual(new_document["supplier"], "SUP-1")
		self.assertEqual(new_document["min_qty"], 10)
		new_price.insert.assert_called_once_with(ignore_permissions=True)

	def test_manual_price_check_queues_partner(self):
		partner = frappe._dict({"name": "Siemens", "validate": 1, "check_permission": Mock()})
		job = Mock(id="job-1")
		with patch("erpnext_oci.open_catalog_interface.price_update.frappe.only_for"), \
			patch("erpnext_oci.open_catalog_interface.price_update.frappe.get_doc", return_value=partner), \
			patch("erpnext_oci.open_catalog_interface.price_update.frappe.enqueue", return_value=job) as enqueue:
			result = enqueue_supplier_price_check("Siemens")
		self.assertEqual(result["job_id"], "job-1")
		self.assertEqual(enqueue.call_args[1]["partner_name"], "Siemens")

	def test_monthly_price_check_enqueues_enabled_partners(self):
		with patch("erpnext_oci.open_catalog_interface.price_update.frappe.get_all", return_value=[frappe._dict({"name": "Siemens"})]) as get_all, \
			patch("erpnext_oci.open_catalog_interface.price_update.frappe.enqueue") as enqueue:
			schedule_monthly_price_checks()
		self.assertEqual(get_all.call_args[1]["filters"], {"validate": 1, "auto_update_purchase_prices": 1})
		self.assertEqual(enqueue.call_args[1]["partner_name"], "Siemens")

	def test_supplier_failure_logs_item_and_error(self):
		partner = frappe._dict({
			"name": "Siemens", "supplier": "SUP-1", "validate": 1,
			"price_check_quantity": 10,
			"fields": [frappe._dict({"fieldtype": "Item-Price", "pricelist": "Standard-Kauf"})],
		})
		database = Mock()
		database.get_value.return_value = frappe._dict({"buying": 1, "currency": "CHF"})
		with patch("erpnext_oci.open_catalog_interface.price_update.frappe.get_doc", return_value=partner), \
			patch("erpnext_oci.open_catalog_interface.price_update.frappe.db", database), \
			patch("erpnext_oci.open_catalog_interface.price_update.frappe.get_all", return_value=[frappe._dict({
				"parent": "ITEM-1", "supplier_part_no": "SUP-PART-1",
			})]), patch("erpnext_oci.open_catalog_interface.price_update.frappe.utils.get_url", return_value="https://erp.example/hook"), \
			patch("erpnext_oci.open_catalog_interface.price_update.request_supplier_validation", side_effect=ValueError("Supplier timeout")), \
			patch("erpnext_oci.open_catalog_interface.price_update.frappe.log_error") as log_error:
			result = run_supplier_price_check("Siemens")
		self.assertEqual(result["errors"], 1)
		self.assertIn("ITEM-1", log_error.call_args[1]["message"])
		self.assertIn("Supplier timeout", log_error.call_args[1]["message"])
