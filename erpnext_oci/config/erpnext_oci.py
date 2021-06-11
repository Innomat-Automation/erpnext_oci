from __future__ import unicode_literals
from frappe import _

def get_data():
    return[
        {
            "label": _("OCI Interface"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "page",
                       "name": "oci_partner",
                       "label": _("OCI Partner"),
                       "description": _("OCI Partner")
                   },
                   {
                       "type": "doctype",
                       "name": "OCI Basket",
                       "label": _("OCI Basket"),
                       "description": _("OCI Basket")
                   }
            ]
        },
        {
            "label": _("Configuration"),
            "icon": "octicon octicon-file-submodule",
            "items": [
                   {
                       "type": "doctype",
                       "name": "OCI Partner",
                       "label": _("OCI Partner"),
                       "description": _("OCI Partner")                   
                   }
            ]
        }
    ]
