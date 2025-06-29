import frappe
from frappe.utils import getdate, get_first_day

def joining_fee_deduction(doc, method):
    if not doc.employee or not doc.start_date:
        return

    salary_month = getdate(doc.start_date).strftime("%Y-%m")

    fee = frappe.get_value("Joining Fee Tracker", {"employee": doc.employee}, ["name"], as_dict=True)
    if not fee:
        return

    tracker = frappe.get_doc("Joining Fee Tracker", fee.name)

    if getdate(tracker.start_month) > getdate(doc.start_date):
        return
    if tracker.amount_paid >= tracker.total_fee:
        return

    emi = tracker.total_fee / tracker.number_of_months
    remaining = tracker.total_fee - tracker.amount_paid
    this_month_deduction = min(emi, remaining)

    if not any(d.salary_component == "Joining Fee EMI" for d in doc.deductions):
        doc.append("deductions", {
            "salary_component": "Joining Fee EMI",
            "amount": this_month_deduction
        })

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

    if total_advance and not any(d.salary_component == "Advance Deduction" for d in doc.deductions):
        doc.append("deductions", {
            "salary_component": "Advance Deduction",
            "amount": total_advance
        })

        for adv in advances:
            frappe.db.set_value("Employee Advance Request", adv.name, "deducted_in_salary", 1)

def mess_deduction(doc, method):
    if not doc.employee or not doc.start_date:
        return

    # Get the first and last day of the salary month
    from frappe.utils import add_months, get_first_day

    start_date = get_first_day(getdate(doc.start_date))
    end_date = get_first_day(add_months(start_date, 1))  # First day of next month

    # Fetch Mess Tracker documents where the 'month' falls in the salary month
    mess_trackers = frappe.get_all("Mess Tracker",
        filters={
            "month": [">=", start_date],
            "month": ["<", end_date]
        },
        fields=["name"]
    )

    total_deduction = 0.0

    for mt in mess_trackers:
        detail = frappe.get_all("Mess Deduction Detail",
            filters={
                "parent": mt.name,
                "employee": doc.employee
            },
            fields=["amount_to_deduct"]
        )
        if detail:
            total_deduction += detail[0].amount_to_deduct

    if total_deduction and not any(d.salary_component == "Mess Deduction" for d in doc.deductions):
        doc.append("deductions", {
            "salary_component": "Mess Deduction",
            "amount": total_deduction
        })

