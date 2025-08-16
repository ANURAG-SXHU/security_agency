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

    salary_month = get_first_day(getdate(doc.start_date))

    # Get the Mess Tracker for the same month as salary slip
    mess_trackers = frappe.get_all("Mess Tracker",
        filters={"month": salary_month},
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

    # Add deduction only if not already added
    if total_deduction and not any(d.salary_component == "Mess Deduction" for d in doc.deductions):
        doc.append("deductions", {
            "salary_component": "Mess Deduction",
            "amount": total_deduction
        })
def add_overtime_from_gps(doc, method):
    # Run only if both employee and dates are set
    if not doc.employee or not doc.start_date or not doc.end_date:
        return

    # Get GPS check-ins for the salary period
    gps_entries = frappe.get_all(
        "GPS Check-in Request",
        filters={
            "employee": doc.employee,
            "check_in_time": ["between", [
                f"{doc.start_date} 00:00:00",
                f"{doc.end_date} 23:59:59"
            ]]
        },
        fields=["site", "check_in_time"]
    )

    if not gps_entries:
        return

    # Count shifts per site
    site_counts = {}
    for entry in gps_entries:
        if not entry.site:
            continue
        site_counts.setdefault(entry.site, 0)
        site_counts[entry.site] += 1

    overtime_amount = 0

    for site_name, count in site_counts.items():
        try:
            site_doc = frappe.get_doc("Site", site_name)
        except frappe.DoesNotExistError:
            continue

        regular_limit = site_doc.regular_shifts or 0
        rate_per_shift = site_doc.overtime_rate_per_shift or 0

        if count > regular_limit:
            overtime_shifts = count - regular_limit
            overtime_amount += overtime_shifts * rate_per_shift

    # Add overtime component if amount > 0
    if overtime_amount > 0:
        # Check if Overtime already exists in earnings
        exists = any(e.salary_component == "Overtime" for e in doc.earnings)
        if not exists:
            doc.append("earnings", {
                "salary_component": "Overtime",
                "amount": overtime_amount
            })

        # Recalculate salary totals
        if hasattr(doc, "calculate_net_pay"):
            doc.calculate_net_pay()

