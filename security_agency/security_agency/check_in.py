import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist(allow_guest=True)
def check_in(latitude=None, longitude=None):
    """
    API to create an 'Automatic Check In' record.
    Uses the logged-in user (via API Key/Secret) to get the employee ID.
    """

    if not latitude or not longitude:
        return {
            "status": "error",
            "message": "Latitude and Longitude are required"
        }

    # ✅ Identify session user (should be API token user)
    user = frappe.session.user
    if user == "Guest":
        return {
            "status": "error",
            "message": "Authentication required (use API Key/Secret)"
        }

    # ✅ Find linked Employee from session user
    employee = frappe.db.get_value("Employee", {"user_id": user})
    if not employee:
        return {
            "status": "error",
            "message": f"No Employee linked to user {user}"
        }

    try:
        # ✅ Create Check-In record
        doc = frappe.get_doc({
            "doctype": "Automatic Check In",
            "employee": employee,
            "latitude": latitude,
            "longitude": longitude,
            "check_in_type": "Manual",
            "check_in_time": now_datetime()
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Check-in recorded for {employee}",
            "employee": employee,
            "docname": doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Check-In API Error")
        return {
            "status": "error",
            "message": str(e)
        }
