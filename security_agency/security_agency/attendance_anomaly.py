import frappe
from frappe.utils import nowdate

def mark_anomaly_for_no_checkin(employee_id, site=None, attendance_date=None):
    """
    Create an Attendance Anomaly if the employee did not check in on the given date.
    """
    if not attendance_date:
        attendance_date = nowdate()

    # Check if attendance exists
    attendance_exists = frappe.db.exists("Attendance", {
        "employee": employee_id,
        "attendance_date": attendance_date,
        "docstatus": 1
    })

    if attendance_exists:
        return  # Already marked present

    # Check if anomaly already exists
    anomaly_exists = frappe.db.exists("Attendance Anomaly", {
        "guard": employee_id,
        "date": attendance_date,
        "type": "No Check-ins"
    })

    if anomaly_exists:
        return  # Already marked as anomaly

    # Create anomaly document
    anomaly = frappe.new_doc("Attendance Anomaly")
    anomaly.date = attendance_date
    anomaly.guard = employee_id
    anomaly.site = site
    anomaly.type = "No Check-ins"
    anomaly.absentee_count = 1
    anomaly.insert(ignore_permissions=True)

    frappe.msgprint(f"⚠️ Attendance Anomaly created for {employee_id} on {attendance_date}")


def check_no_show_employees(site, date=None):
    """
    Check all guards assigned to a site and mark anomalies if they did not check in.
    """
    if not date:
        date = nowdate()

    # Replace this with your actual assignment DocType
    assigned_employees = frappe.get_all("Employee Site Assignment", {
        "site": site
    }, ["employee"])

    for emp in assigned_employees:
        mark_anomaly_for_no_checkin(emp.employee, site=site, attendance_date=date)


def mark_daily_anomalies_for_all_sites():
    """
    Daily scheduler to mark anomalies for all sites.
    """
    all_sites = frappe.get_all("Site", pluck="name")
    today = nowdate()

    for site in all_sites:
        check_no_show_employees(site, date=today)
