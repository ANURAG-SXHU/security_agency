import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist(allow_guest=False)
def check_in(latitude=None, longitude=None, user_email=None):
    """
    ✅ Check-in API:
    Auth via API key (e.g., mobile.checkin@mtss.com),
    But actual check-in is for user_email → employee.
    """

    # Validation
    if not latitude or not longitude or not user_email:
        return {
            "status": "error",
            "message": "Latitude, Longitude, and user_email are required"
        }

    # Ensure user_email is valid
    if not frappe.db.exists("User", user_email):
        return {
            "status": "error",
            "message": f"User '{user_email}' does not exist"
        }

    # Find Employee linked to user_email
    employee = frappe.db.get_value("Employee", {"user_id": user_email})
    if not employee:
        return {
            "status": "error",
            "message": f"No Employee found for user '{user_email}'"
        }

    try:
        # Create Automatic Check In document
        checkin = frappe.get_doc({
            "doctype": "Automatic Check In",
            "employee": employee,
            "latitude": latitude,
            "longitude": longitude,
            "checkin_time": now_datetime()
        })
        checkin.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Check-in recorded for {employee}",
            "employee": employee,
            "docname": checkin.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Automatic Check In API Error")
        return {
            "status": "error",
            "message": str(e)
        }
