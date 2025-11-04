import frappe
from frappe.utils import getdate, get_first_day
import calendar
from datetime import date

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
# def add_overtime_from_gps(doc, method):
#     # Run only if both employee and dates are set
#     if not doc.employee or not doc.start_date or not doc.end_date:
#         return

#     # Get GPS check-ins for the salary period
#     gps_entries = frappe.get_all(
#         "GPS Check-in Request",
#         filters={
#             "employee": doc.employee,
#             "check_in_time": ["between", [
#                 f"{doc.start_date} 00:00:00",
#                 f"{doc.end_date} 23:59:59"
#             ]]
#         },
#         fields=["site", "check_in_time"]
#     )

#     if not gps_entries:
#         return

#     # Count shifts per site
#     site_counts = {}
#     for entry in gps_entries:
#         if not entry.site:
#             continue
#         site_counts.setdefault(entry.site, 0)
#         site_counts[entry.site] += 1

#     overtime_amount = 0

#     for site_name, count in site_counts.items():
#         try:
#             site_doc = frappe.get_doc("Site", site_name)
#         except frappe.DoesNotExistError:
#             continue

#         regular_limit = site_doc.regular_shifts or 0
#         rate_per_shift = site_doc.overtime_rate_per_shift or 0

#         if count > regular_limit:
#             overtime_shifts = count - regular_limit
#             overtime_amount += overtime_shifts * rate_per_shift

#     # Add overtime component if amount > 0
#     if overtime_amount > 0:
#         # Check if Overtime already exists in earnings
#         exists = any(e.salary_component == "Overtime" for e in doc.earnings)
#         if not exists:
#             doc.append("earnings", {
#                 "salary_component": "Overtime",
#                 "amount": overtime_amount
#             })

#         # Recalculate salary totals
#         if hasattr(doc, "calculate_net_pay"):
#             doc.calculate_net_pay()


# def add_overtime_from_gps(doc, method):
#     if not doc.employee or not doc.start_date or not doc.end_date:
#         print("❌ Missing employee or date range — skipping overtime calculation.")
#         return

#     gps_entries = frappe.get_all(
#         "GPS Check-in Request",
#         filters={
#             "employee": doc.employee,
#             "check_in_time": ["between", [
#                 f"{doc.start_date} 00:00:00",
#                 f"{doc.end_date} 23:59:59"
#             ]]
#         },
#         fields=["site", "check_in_time", "shift_type"],
#         order_by="check_in_time asc"
#     )

#     print(f"\n📋 Found {len(gps_entries)} GPS entries for {doc.employee}")

#     if not gps_entries:
#         return

#     # Group by site
#     site_entries = {}
#     for entry in gps_entries:
#         if not entry.site:
#             continue
#         site_entries.setdefault(entry.site, [])
#         site_entries[entry.site].append(entry)

#     total_overtime_amount = 0

#     for site_name, entries in site_entries.items():
#         try:
#             site_doc = frappe.get_doc("Site", site_name)
#         except frappe.DoesNotExistError:
#             print(f"⚠️ Site '{site_name}' not found, skipping.")
#             continue

#         regular_limit = site_doc.get("regular_shifts") or 0
#         rate_per_shift = site_doc.get("overtime_rate_per_shift") or 0

#         print(f"\n🏢 Site: {site_name}")
#         print(f"➡ Regular Limit: {regular_limit}, Rate/Shift: ₹{rate_per_shift}, Total Shifts: {len(entries)}")

#         # Compute weighted shift count (half = 0.5)
#         total_equivalent_shifts = 0
#         for e in entries:
#             shift_name = (e.shift_type or "").strip()
#             is_half = 0
#             if shift_name:
#                 is_half = frappe.db.get_value("Shift Type", shift_name, "half_shift") or 0
#             total_equivalent_shifts += 0.5 if is_half else 1

#         print(f"🧮 Equivalent Shifts Worked: {total_equivalent_shifts}")

#         if total_equivalent_shifts <= regular_limit:
#             print("✅ No overtime for this site.")
#             continue

#         overtime_equiv = total_equivalent_shifts - regular_limit
#         site_overtime = overtime_equiv * rate_per_shift

#         print(f"💰 Overtime Equivalent: {overtime_equiv} × ₹{rate_per_shift} = ₹{site_overtime}\n")
#         total_overtime_amount += site_overtime

#     if total_overtime_amount > 0:
#         existing_row = next((e for e in doc.earnings if e.salary_component == "Overtime"), None)
#         if existing_row:
#             existing_row.amount = total_overtime_amount
#         else:
#             doc.append("earnings", {
#                 "salary_component": "Overtime",
#                 "amount": total_overtime_amount
#             })

#         if hasattr(doc, "calculate_net_pay"):
#             doc.calculate_net_pay()

#         print(f"✅ Final Overtime Added: ₹{total_overtime_amount:.2f}")
#         frappe.msgprint(f"💸 Auto Overtime Added: ₹{total_overtime_amount:.2f}", indicator="green")
#     else:
#         print("ℹ️ No overtime detected for this employee.")

def add_overtime_from_gps(doc, method):
    if not doc.employee or not doc.start_date or not doc.end_date:
        print("❌ Missing employee or date range — skipping overtime calculation.")
        return

    # ✅ Only include Approved check-ins
    valid_workflow_states = ["Approved(Guard)", "Approved(Supervisor)"]

    gps_entries = frappe.get_all(
        "GPS Check-in Request",
        filters={
            "employee": doc.employee,
            "workflow_state": ["in", valid_workflow_states],
            "check_in_time": ["between", [
                f"{doc.start_date} 00:00:00",
                f"{doc.end_date} 23:59:59"
            ]]
        },
        fields=["site", "check_in_time", "shift_type", "workflow_state"],
        order_by="check_in_time asc"
    )

    print(f"\n📋 Found {len(gps_entries)} Approved GPS entries for {doc.employee}")
    if not gps_entries:
        print("ℹ️ No approved GPS entries found. Skipping overtime calculation.")
        return

    # Group by site
    site_entries = {}
    for entry in gps_entries:
        if not entry.site:
            continue
        site_entries.setdefault(entry.site, [])
        site_entries[entry.site].append(entry)

    total_overtime_amount = 0

    for site_name, entries in site_entries.items():
        try:
            site_doc = frappe.get_doc("Site", site_name)
        except frappe.DoesNotExistError:
            print(f"⚠️ Site '{site_name}' not found, skipping.")
            continue

        regular_limit = site_doc.get("regular_shifts") or 0
        rate_per_shift = site_doc.get("overtime_rate_per_shift") or 0

        print(f"\n🏢 Site: {site_name}")
        print(f"➡ Regular Limit: {regular_limit}, Rate/Shift: ₹{rate_per_shift}, Total Approved Shifts: {len(entries)}")

        # Compute weighted shift count (half = 0.5)
        total_equivalent_shifts = 0
        for e in entries:
            shift_name = (e.shift_type or "").strip()
            is_half = 0
            if shift_name:
                is_half = frappe.db.get_value("Shift Type", shift_name, "half_shift") or 0
            total_equivalent_shifts += 0.5 if is_half else 1

        print(f"🧮 Equivalent Shifts Worked: {total_equivalent_shifts}")

        if total_equivalent_shifts <= regular_limit:
            print("✅ No overtime for this site.")
            continue

        overtime_equiv = total_equivalent_shifts - regular_limit
        site_overtime = overtime_equiv * rate_per_shift

        print(f"💰 Overtime Equivalent: {overtime_equiv} × ₹{rate_per_shift} = ₹{site_overtime}\n")
        total_overtime_amount += site_overtime

    if total_overtime_amount > 0:
        existing_row = next((e for e in doc.earnings if e.salary_component == "Overtime"), None)
        if existing_row:
            existing_row.amount = total_overtime_amount
        else:
            doc.append("earnings", {
                "salary_component": "Overtime",
                "amount": total_overtime_amount
            })

        if hasattr(doc, "calculate_net_pay"):
            doc.calculate_net_pay()

        print(f"✅ Final Overtime Added: ₹{total_overtime_amount:.2f}")
        frappe.msgprint(f"💸 Auto Overtime Added: ₹{total_overtime_amount:.2f}", indicator="green")
    else:
        print("ℹ️ No overtime detected for this employee.")

def update_regular_shifts_and_overtime_rate():
    """
    Automatically update:
    - regular_shifts = number of days in the current month
    - overtime_rate_per_shift = salary / number_of_days_in_month
    """
    today = date.today()
    year, month = today.year, today.month

    # Get total number of days in this month
    total_days = calendar.monthrange(year, month)[1]
    month_name = calendar.month_name[month]

    # Fetch all sites
    sites = frappe.get_all("Site", fields=["name", "salary"])

    if not sites:
        frappe.logger().info("⚠️ No Site records found for monthly update.")
        return

    for s in sites:
        # --- Update regular_shifts ---
        frappe.db.set_value("Site", s.name, "regular_shifts", total_days)

        # --- Update overtime_rate_per_shift ---
        salary = 0
        try:
            salary = float(s.salary or 0)
        except:
            salary = 0

        overtime_rate = 0
        if salary > 0:
            overtime_rate = round(salary / total_days, 2)

        frappe.db.set_value("Site", s.name, "overtime_rate_per_shift", overtime_rate)

        frappe.logger().info(
            f"🏢 Site: {s.name} | Month: {month_name} | Days: {total_days} | "
            f"Salary: ₹{salary} | Overtime/Shift: ₹{overtime_rate}"
        )

    frappe.db.commit()

    frappe.logger().info(
        f"✅ Updated {len(sites)} sites — Regular Shifts: {total_days}, "
        f"Overtime Rate calculated for {month_name} {year}"
    )

    frappe.msgprint(
        f"✅ Auto-updated {len(sites)} sites: Regular Shifts = {total_days}, "
        f"Overtime Rate = Salary ÷ {total_days} ({month_name})",
        indicator="green"
    )
