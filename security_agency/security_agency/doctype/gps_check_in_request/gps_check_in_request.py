import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, formatdate, now_datetime
from frappe import _
from datetime import datetime
from frappe.utils import nowdate, now_datetime

class GPSCheckinRequest(Document):
    def before_save(self):
        if self.shift_type:
            return

        # Safely convert string to datetime
        check_in_dt = get_datetime(self.check_in_time)
        weekday = check_in_dt.strftime("%A")
        check_in_time_only = check_in_dt.time()

        # Find Deployment Sheet for week
        sheet = frappe.db.get_value(
            "Deployment Sheet",
            {
                "week_start_date": ["<=", check_in_dt.date()],
                "week_end_date": [">=", check_in_dt.date()],
            },
            "name"
        )
        if not sheet:
            frappe.throw(_("No Deployment Sheet found for this week."))

        # Find Deployment Line for this guard, site, day
        shift_name = frappe.db.get_value(
            "Deployment Line",
            {
                "parent": sheet,
                "guard": self.employee,
                "site": self.site,
                "day": weekday
            },
            "shift"
        )
        if not shift_name:
            frappe.throw(_("No Deployment Line found for this guard/site/day."))

        # Get Shift timings
        shift = frappe.get_doc("Shift Type", shift_name)
        shift_start = datetime.strptime(str(shift.start_time), "%H:%M:%S").time()
        shift_end = datetime.strptime(str(shift.end_time), "%H:%M:%S").time()

        # Check if check-in time fits shift (incl. overnight)
        if shift_start < shift_end:
            valid = shift_start <= check_in_time_only <= shift_end
        else:
            valid = check_in_time_only >= shift_start or check_in_time_only <= shift_end

        if not valid:
            frappe.throw(_("Check-in time does not fall within shift hours for {0}.").format(shift_name))

        self.shift_type = shift_name

    def autoname(self):
        if not self.check_in_time:
            self.check_in_time = now_datetime()

        date_str = formatdate(self.check_in_time, "yyyyMMdd")
        emp_name = frappe.db.get_value("Employee", self.employee, "employee_name") or "UNKNOWN"
        self.name = f"{emp_name.replace(' ', '').upper()}-{date_str}"

    def before_insert(self):
        self.workflow_state = "Draft"

    def on_update_after_submit(self):
        if self.workflow_state in ["Approved(Guard)", "Approved(Supervisor)"]:
            if not self.employee:
                frappe.msgprint("❌ Employee is missing. Cannot create attendance.")
                return

            create_attendance_for_employee(
                employee_id=self.employee,
                attendance_datetime=self.check_in_time or now_datetime(),
                ref_doctype=self.doctype,
                ref_name=self.name
            )
            frappe.msgprint("✅ Attendance created.")



@frappe.whitelist()
# def create_attendance_for_employee(employee_id, attendance_datetime, ref_doctype=None, ref_name=None):
#     if not employee_id:
#         frappe.msgprint("❌ Employee ID is missing.")
#         return

#     check_in_dt = get_datetime(attendance_datetime)
#     attendance_date = check_in_dt.date()

#     exists = frappe.db.exists("Attendance", {
#         "employee": employee_id,
#         "attendance_date": attendance_date,
#         "docstatus": 1
#     })
#     if exists:
#         frappe.msgprint(f"ℹ️ Attendance already exists for {employee_id} on {attendance_date}.")
#         return

#     employee = frappe.get_doc("Employee", employee_id)

#     # If reference is a GPS Check-in Request, pull shift_type from it
#     shift = None
#     if ref_doctype == "GPS Check-in Request" and ref_name:
#         shift = frappe.db.get_value("GPS Check-in Request", ref_name, "shift_type")

#     attendance = frappe.new_doc("Attendance")
#     attendance.naming_series = "HR-ATT-.YYYY.-"
#     attendance.employee = employee_id
#     attendance.attendance_date = attendance_date
#     attendance.status = "Present"
#     attendance.company = employee.company or "Default Company"
#     attendance.department = employee.department or "General"
#     attendance.in_time = check_in_dt

#     if shift:
#         attendance.shift = shift

#     if frappe.get_meta("Attendance").has_field("reference_doctype"):
#         attendance.reference_doctype = ref_doctype
#     if frappe.get_meta("Attendance").has_field("reference_name"):
#         attendance.reference_name = ref_name

#     attendance.insert(ignore_permissions=True)
#     attendance.submit()

#     frappe.msgprint(f"✅ Attendance submitted for {employee_id} on {attendance_date}.")
def create_attendance_for_employee(
    employee_id,
    attendance_date=None,
    status='Present',
    ref_doctype=None,
    ref_name=None,
    attendance_datetime=None
):
    if not attendance_date:
        attendance_date = nowdate()

    # Fetch shift from the referenced document (e.g., GPS Check-in Request)
    shift = None
    if ref_doctype == "GPS Check-in Request" and ref_name:
        shift = frappe.db.get_value("GPS Check-in Request", ref_name, "shift_type")

    if not shift:
        frappe.msgprint("⚠️ Shift not found. Cannot check for duplicates.")
        return

    # Check if attendance already exists for the same employee, date, and shift
    exists = frappe.db.exists("Attendance", {
        "employee": employee_id,
        "attendance_date": attendance_date,
        "shift": shift,
        "docstatus": 1
    })

    if exists:
        frappe.msgprint(f"ℹ️ Attendance already exists for {employee_id} on {attendance_date} for shift {shift}.")
        return

    # Create Attendance document
    attendance = frappe.get_doc({
        "doctype": "Attendance",
        "employee": employee_id,
        "attendance_date": attendance_date,
        "status": status,
        "shift": shift,
        "company": frappe.db.get_value("Employee", employee_id, "company"),
        "gps_checkin_ref": ref_name if ref_doctype == "GPS Check-in Request" else None,
        "check_in_by": frappe.session.user,
        "in_time": attendance_datetime or now_datetime()  # Optional use of GPS check-in time
    })

    attendance.insert()
    attendance.submit()
    frappe.msgprint(f"✅ Attendance marked for {employee_id} on {attendance_date} for shift {shift}.")

# ------------------------
# GPS Check-in Request Permissions
# ------------------------

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    if user in ["Administrator", "Admin"]:
        return None

    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not emp_id:
        return "1=0"

    return (
        f"`tabGPS Check-in Request`.employee = '{emp_id}' "
        f"OR `tabGPS Check-in Request`.repoting_to = '{emp_id}'"
    )


def has_permission(doc, ptype, user):
    if user in ["Administrator", "Admin"]:
        return True

    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if ptype == "create":
        return True
    return doc.employee == emp_id or doc.repoting_to == emp_id


# ------------------------
# Employee Permissions
# ------------------------

def get_employee_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    if user in ["Administrator", "Admin"]:
        return None

    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return f"`tabEmployee`.name = '{emp_id}'" if emp_id else "1=0"


def has_employee_permission(doc, ptype, user):
    if user in ["Administrator", "Admin"]:
        return True

    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return doc.name == emp_id


# ------------------------
# Attendance Permissions
# ------------------------

def get_attendance_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    if user in ["Administrator", "Admin"]:
        return None

    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return f"`tabAttendance`.employee = '{emp_id}'" if emp_id else "1=0"


def has_attendance_permission(doc, ptype, user):
    if user in ["Administrator", "Admin"]:
        return True

    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return doc.employee == emp_id
