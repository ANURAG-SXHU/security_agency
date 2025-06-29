# security_agency/custom_hooks.py

import frappe
from frappe.utils import getdate

def joining_fee_deduction(doc, method):
    if not doc.employee or not doc.start_date:
        return

    # Get salary month in YYYY-MM format
    salary_month = getdate(doc.start_date).strftime("%Y-%m")

    # Get Joining Fee Tracker (only one per employee expected)
    fee = frappe.get_value("Joining Fee Tracker", {"employee": doc.employee}, ["name"], as_dict=True)
    if not fee:
        return

    tracker = frappe.get_doc("Joining Fee Tracker", fee.name)

    # Skip if fee not started or already paid
    if getdate(tracker.start_month) > getdate(doc.start_date):
        return
    if tracker.amount_paid >= tracker.total_fee:
        return

    # Calculate EMI
    emi = tracker.total_fee / tracker.number_of_months
    remaining = tracker.total_fee - tracker.amount_paid
    this_month_deduction = min(emi, remaining)

    # Check if already added (avoid duplicates)
    if not any(d.salary_component == "Joining Fee EMI" for d in doc.deductions):
        doc.append("deductions", {
            "salary_component": "Joining Fee EMI",
            "amount": this_month_deduction
        })

        # Update amount paid immediately (you can also do this in `on_submit`)
        tracker.amount_paid += this_month_deduction
        tracker.save()
def advance_request_deduction(doc, method):
    if not doc.employee or not doc.start_date:
        return

    from_date = getdate(doc.start_date)
    to_date = getdate(doc.end_date)

    advances = frappe.get_all("Employee Advance Request",
        filters={
            "employee": doc.employee,
            "posting_date": ["between", [from_date, to_date]],
            "workflow_state": "Approved By HR",
            "docstatus": 1
        },
        fields=["name", "advance_amount"]
    )

    total_advance = sum(a.advance_amount for a in advances)

    # Avoid duplicate entry
    if total_advance and not any(d.salary_component == "Advance Deduction" for d in doc.deductions):
        doc.append("deductions", {
            "salary_component": "Advance Deduction",
            "amount": total_advance
        })

        # Optional: mark advance as deducted
        for adv in advances:
            frappe.db.set_value("Employee Advance Request", adv.name, "deducted_in_salary", 1)
def mess_tracker_deduction(doc, method):
    if not doc.employee or not doc.start_date:
        return

    salary_month = getdate(doc.start_date).strftime("%Y-%m")

    # Fetch all approved Mess Trackers for the salary month
    mess_docs = frappe.get_all("Mess Tracker",
        filters={
            "workflow_state": "Approved",
            "posting_date": ["like", f"{salary_month}%"],
            "docstatus": 1
        },
        fields=["name"]
    )

    total_deduction = 0

    for mess_doc in mess_docs:
        mess = frappe.get_doc("Mess Tracker", mess_doc.name)
        for row in mess.employee_deductions:
            if row.employee == doc.employee and row.amount:
                total_deduction += row.amount

    # Only add deduction if not already added
    if total_deduction > 0 and not any(d.salary_component == "Mess Deduction" for d in doc.deductions):
        doc.append("deductions", {
            "salary_component": "Mess Deduction",
            "amount": total_deduction
        })

