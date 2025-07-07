import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def check_in(latitude=None, longitude=None):
    """
    Public API to create an 'Automatic Check In' record.
    No authentication required.
    """

    if not latitude or not longitude:
        return {
            "status": "error",
            "message": "Latitude and Longitude are required"
        }

    try:
        # Create the document
        doc = frappe.get_doc({
            "doctype": "Automatic Check In",
            "latitude": latitude,
            "longitude": longitude,
            "check_in_type": "Manual",  # optional
            "check_in_time": frappe.utils.now_datetime()
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Check-in recorded at lat={latitude}, long={longitude}",
            "docname": doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Check-In API Error")
        return {
            "status": "error",
            "message": str(e)
        }
