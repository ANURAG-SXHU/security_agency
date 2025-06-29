# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class JoiningFeeTracker(Document):

    def validate(self):
        # Ensure fields are present
        if self.total_fee and self.number_of_months:
            self.monthly_emi = round(self.total_fee / self.number_of_months, 2)
        else:
            self.monthly_emi = 0

        if self.amount_paid is None:
            self.amount_paid = 0

        self.balance = self.total_fee - self.amount_paid

        if self.balance < 0:
            frappe.throw("Amount Paid cannot exceed Total Fee.")
