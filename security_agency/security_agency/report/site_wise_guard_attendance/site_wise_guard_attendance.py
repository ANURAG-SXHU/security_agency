# Copyright (c) 2025, Anurag Sahu
# For license information, please see license.txt

# import frappe
# from frappe.utils import getdate

# def execute(filters=None):
#     columns = get_columns()
#     if not filters:
#         return columns, []

#     site = filters.get("site")
#     date = getdate(filters.get("date"))

#     if not site or not date:
#         return columns, [["Please select both Site and Date"]]

#     day_name = date.strftime("%A")

#     # Step 1: Get Deployment Sheet containing the selected date
#     deployment_sheet = frappe.get_all("Deployment Sheet", filters={
#         "week_start_date": ["<=", date],
#         "week_end_date": [">=", date]
#     }, fields=["name"])

#     if not deployment_sheet:
#         return columns, [["No Deployment Sheet found for the selected date."]]

#     sheet_name = deployment_sheet[0]["name"]

#     # Step 2: Get deployed guards for the selected site and day
#     deployed_guards = frappe.get_all("Deployment Line", filters={
#         "parent": sheet_name,
#         "site": site,
#         "day": day_name
#     }, fields=["guard"])

#     if not deployed_guards:
#         return columns, [["No guards deployed to this site on this day."]]

#     deployed_guard_ids = [g["guard"] for g in deployed_guards if g.get("guard")]

#     # Step 3: Get Guard Names
#     employee_names = frappe.get_all("Employee", filters={
#         "name": ["in", deployed_guard_ids]
#     }, fields=["name", "employee_name"])

#     name_map = {e["name"]: e["employee_name"] for e in employee_names}

#     # Step 4: Get GPS Check-ins with workflow_state = "Approved (Supervisor)"
#     checkins = frappe.get_all("GPS Check-in Request", filters={
#         "site": site,
#         "workflow_state": "Approved (Supervisor)",
#         "check_in_time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
#     }, fields=["employee"])

#     present_ids = set([c["employee"] for c in checkins])

#     # Step 5: Compile Attendance Data
#     data = []
#     for guard_id in deployed_guard_ids:
#         emp_name = name_map.get(guard_id, "Unknown")
#         status = "Present" if guard_id in present_ids else "Absent"
#         data.append([guard_id, emp_name, status])

#     return columns, data

# def get_columns():
#     return [
#         {"label": "Guard ID", "fieldname": "guard", "fieldtype": "Link", "options": "Employee", "width": 150},
#         {"label": "Guard Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
#         {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100}
#     ]
# Copyright (c) 2025, Anurag Sahu
# For license information, please see license.txt
import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = get_columns()

    if not filters:
        return columns, [["⚠️ Please select both Site and Date"]]

    site = filters.get("site")
    date = getdate(filters.get("date"))

    if not site or not date:
        return columns, [["⚠️ Please select both Site and Date"]]

    day_name = date.strftime("%A")

    # Step 1: Get Deployment Sheet for selected date
    deployment_sheet = frappe.get_value("Deployment Sheet", {
        "week_start_date": ["<=", date],
        "week_end_date": [">=", date]
    }, "name")

    if not deployment_sheet:
        return columns, [["❌ No Deployment Sheet found for the selected date."]]

    # Step 2: Get guards deployed at the site for the specific day
    deployed_guards = frappe.get_all("Deployment Line", filters={
        "parent": deployment_sheet,
        "site": site,
        "day": day_name
    }, fields=["guard"])

    if not deployed_guards:
        return columns, [["❌ No guards deployed to this site on this day."]]

    deployed_guard_ids = [g["guard"] for g in deployed_guards if g.get("guard")]

    # Step 3: Fetch guard names
    employee_names = frappe.get_all("Employee", filters={
        "name": ["in", deployed_guard_ids]
    }, fields=["name", "employee_name"])

    name_map = {e["name"]: e["employee_name"] for e in employee_names}

    # Step 4: Fetch GPS Check-ins (no workflow state filter)
    checkins = frappe.get_all("GPS Check-in Request", filters={
        "site": site,
        "check_in_time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
    }, fields=["employee"])

    present_ids = {c["employee"] for c in checkins if c.get("employee")}

    # Step 5: Build report rows
    data = []
    for guard_id in deployed_guard_ids:
        emp_name = name_map.get(guard_id, "Unknown")
        status = "Present" if guard_id in present_ids else "Absent"
        data.append([guard_id, emp_name, status])

    return columns, data

def get_columns():
    return [
        {"label": "Guard ID", "fieldname": "guard", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "Guard Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100}
    ]

