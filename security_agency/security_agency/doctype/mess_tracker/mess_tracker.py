# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MessTracker(Document):
    pass

@frappe.whitelist()
def get_guards_server(docname):
    # Get the Mess Tracker document
    doc = frappe.get_doc("Mess Tracker", docname)

    # Clear existing child rows
    doc.set("deduction_table", [])

    # Fetch guards from Employee
    guards = frappe.get_list(
        "Employee",
        filters={
            "reports_to": doc.reports_to
        },
        fields=["name", "employee_name"]
    )


    # Add guards to child table
    for g in guards:
        row = doc.append("deduction_table", {})
        row.employee = g.name
        row.employee_name = g.employee_name
        row.amount_to_deduct = 0

    # Auto distribute amount if required
    if doc.distribute_mode == "Equal" and doc.total_amount:
        total_people = len(doc.deduction_table)
        if total_people > 0:
            per_person = doc.total_amount / total_people
            for row in doc.deduction_table:
                row.amount_to_deduct = round(per_person, 2)

    # Save updated doc
    doc.save(ignore_permissions=True)

    # Return full updated document
    return doc

