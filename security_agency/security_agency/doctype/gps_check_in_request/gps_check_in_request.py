import frappe
from frappe.model.document import Document
from frappe.utils import formatdate, now_datetime
from frappe import _

class GPSCheckinRequest(Document):

    def autoname(self):
        if not self.check_in_time:
            self.check_in_time = now_datetime()

        date_str = formatdate(self.check_in_time, "yyyyMMdd")
        emp_name = "UNKNOWN"
        if self.employee:
            emp = frappe.get_doc("Employee", self.employee)
            emp_name = emp.employee_name.replace(" ", "").upper()
        self.name = f"{emp_name}-{date_str}"

    def before_insert(self):
        self.workflow_state = "Draft"

    def on_update_after_submit(self):
        if self.workflow_state in ["Approved(Guard)", "Approved(Supervisor)"]:
            if not self.employee:
                frappe.msgprint("❌ Employee is missing. Cannot create attendance.")
                return

            frappe.msgprint("✅ Creating attendance...")
            create_attendance_for_employee(
                employee_id=self.employee,
                attendance_datetime=self.check_in_time or now_datetime(),
                ref_doctype=self.doctype,
                ref_name=self.name
            )


@frappe.whitelist()

def create_attendance_for_employee(employee_id, attendance_datetime, ref_doctype=None, ref_name=None):
    if not employee_id:
        frappe.msgprint("❌ Employee ID is missing.")
        return

    attendance_date = attendance_datetime.date()
    exists = frappe.db.exists("Attendance", {
        "employee": employee_id,
        "attendance_date": attendance_date,
        "docstatus": 1
    })

    if exists:
        frappe.msgprint(f"ℹ️ Attendance already exists for {employee_id} on {attendance_date}")
        return

    try:
        employee = frappe.get_doc("Employee", employee_id)
    except Exception as e:
        frappe.msgprint(f"❌ Error loading employee: {str(e)}")
        return

    attendance = frappe.new_doc("Attendance")
    attendance.naming_series = "HR-ATT-.YYYY.-"
    attendance.employee = employee_id
    attendance.attendance_date = attendance_date
    attendance.status = "Present"
    attendance.company = employee.company or "Default Company"
    attendance.department = employee.department or "General"
    attendance.in_time = attendance_datetime

    if frappe.get_meta("Attendance").has_field("reference_doctype"):
        attendance.reference_doctype = ref_doctype
    if frappe.get_meta("Attendance").has_field("reference_name"):
        attendance.reference_name = ref_name

    attendance.insert(ignore_permissions=True)
    attendance.submit()

    frappe.msgprint(f"✅ Attendance created for {employee_id} on {attendance_date}")



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
        return True  # allow Supervisor to create new documents

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


