# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MessTracker(Document):
    def autoname(self):
        emp_id = (self.reports_to or "EMP").replace(" ", "").upper()

        if self.month:
            date_str = frappe.utils.formatdate(self.month, "yyyyMM")
        else:
            date_str = frappe.utils.now_datetime().strftime("%Y%m")

        self.name = f"{emp_id}-{date_str}-{frappe.model.naming.make_autoname('####')}"


