# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class MessTracker(Document):
    pass  # Keep logic minimal in class; use whitelisted function below

@frappe.whitelist()
def fetch_reporting_employees(total_amount):
    user = frappe.session.user

    # Get the Employee ID linked to the current session user
    employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee_id:
        frappe.throw("No Employee record found for the current user.")

    # Fetch employees who report to this employee
    reporting_employees = frappe.get_all(
        "Employee",
        filters={"reports_to": employee_id, "status": "Active"},
        fields=["name", "employee_name"]
    )

    if not reporting_employees:
        frappe.throw("No reporting employees found.")

    # Calculate per-head deduction
    per_head_amount = float(total_amount) / len(reporting_employees)

    return [
        {
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "amount_to_deduct": per_head_amount
        }
        for emp in reporting_employees
    ]
