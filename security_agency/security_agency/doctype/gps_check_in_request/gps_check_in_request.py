import frappe
from frappe.model.document import Document
from frappe.utils import (
    formatdate,
    now_datetime,
    nowdate
)
from frappe import _


# --------------------------------------------------
# GPS CHECK-IN REQUEST
# --------------------------------------------------

class GPSCheckinRequest(Document):

    def before_save(self):
        """
        Guard action only:
        - Block GPS if no rotation exists
        - Resolve planned shift via rotation
        - Set actual shift only if Present
        """

        # 🔁 Local import to avoid circular import
        from security_agency.api.shift_rotation import (
            resolve_planned_shift,
            rotation_exists
        )

        # -------------------------------
        # 0️⃣ Default attendance status
        # -------------------------------
        if not self.attendance_status:
            self.attendance_status = "Present"

        # -------------------------------
        # 1️⃣ BLOCK if rotation missing
        # -------------------------------
        if not rotation_exists(
            site=self.site,
            guard=self.employee,
            check_in_time=self.check_in_time
        ):
            frappe.throw(
                _(
                    "No shift rotation is assigned to you for this site and day.\n"
                    "Please contact your supervisor."
                ),
                title=_("Shift Rotation Missing")
            )

        # -------------------------------
        # 2️⃣ Resolve planned shift ONCE
        # -------------------------------
        if not self.planned_shift_type:
            self.planned_shift_type = resolve_planned_shift(
                site=self.site,
                guard=self.employee,
                check_in_time=self.check_in_time
            )

        if not self.planned_shift_type:
            frappe.throw(
                _("Unable to resolve your shift. Please contact supervisor."),
                title=_("Shift Resolution Failed")
            )

        # -------------------------------
        # 3️⃣ Attendance decision (FIXED)
        # -------------------------------
        if self.attendance_status == "Present":
            self.shift_type = self.planned_shift_type
        else:
            # ❌ DO NOT store "Absent" in Link field
            self.shift_type = None

    # --------------------------------------------------
    # AUTONAME
    # --------------------------------------------------

    def autoname(self):
        if not self.check_in_time:
            self.check_in_time = now_datetime()

        date_str = formatdate(self.check_in_time, "yyyyMMdd")

        emp_name = frappe.db.get_value(
            "Employee",
            self.employee,
            "employee_name"
        ) or "UNKNOWN"

        base = f"{emp_name.replace(' ', '').upper()}-{date_str}"

        existing = frappe.db.sql(
            """
            SELECT name
            FROM `tabGPS Check-in Request`
            WHERE name LIKE %s
            """,
            (f"{base}-%",),
        )

        seq = len(existing) + 1
        self.name = f"{base}-{str(seq).zfill(3)}"

    # --------------------------------------------------
    # WORKFLOW
    # --------------------------------------------------

    def before_insert(self):
        self.workflow_state = "Draft"

    def on_update_after_submit(self):
        """
        Attendance is created ONLY after approval
        """

        if self.workflow_state not in (
            "Approved(Guard)",
            "Approved(Supervisor)"
        ):
            return

        if not self.employee:
            frappe.msgprint(_("Employee missing. Attendance not created."))
            return

        create_attendance_for_employee(
            employee_id=self.employee,
            attendance_datetime=self.check_in_time or now_datetime(),
            ref_doctype=self.doctype,
            ref_name=self.name
        )

        frappe.msgprint(_("Attendance created."))
@frappe.whitelist()
def create_attendance_for_employee(
    employee_id,
    attendance_date=None,
    ref_doctype=None,
    ref_name=None,
    attendance_datetime=None
):
    from frappe.utils import getdate, nowdate

    # ----------------------------------
    # 1️⃣ Resolve correct attendance date
    # ----------------------------------
    if not attendance_date and attendance_datetime:
        attendance_date = getdate(attendance_datetime)
    elif not attendance_date:
        attendance_date = nowdate()

    # ----------------------------------
    # 2️⃣ Fetch shift & site from GPS
    # ----------------------------------
    planned_shift, site = frappe.db.get_value(
        "GPS Check-in Request",
        ref_name,
        ["planned_shift_type", "site"]
    )

    # ❌ Absent → no attendance
    if not planned_shift:
        return

    # ----------------------------------
    # 3️⃣ Prevent duplicates
    # ----------------------------------
    if frappe.db.exists(
        "Attendance",
        {
            "employee": employee_id,
            "attendance_date": attendance_date,
            "docstatus": 1,
        }
    ):
        return

    company = frappe.db.get_value("Employee", employee_id, "company")

    # ----------------------------------
    # 4️⃣ Create attendance
    # ----------------------------------
    attendance = frappe.get_doc({
        "doctype": "Attendance",
        "employee": employee_id,
        "attendance_date": attendance_date,
        "status": "Present",
        "shift": planned_shift,   # ✔ uses Shift Type (valid link)
        "company": company,
        "in_time": attendance_datetime,
        "custom_site": site,
        "gps_checkin_ref": ref_name,
    })

    attendance.insert(ignore_permissions=True)
    attendance.submit()

# --------------------------------------------------
# GPS CHECK-IN PERMISSIONS
# --------------------------------------------------

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if any(
        role in frappe.get_roles(user)
        for role in ("Administrator", "Admin", "Operation Manager")
    ):
        return None

    emp_id = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name"
    )

    if not emp_id:
        return "1=0"

    return (
        f"`tabGPS Check-in Request`.employee = '{emp_id}' "
        f"OR `tabGPS Check-in Request`.repoting_to = '{emp_id}'"
    )


def has_permission(doc, ptype, user):
    if any(
        role in frappe.get_roles(user)
        for role in ("Administrator", "Admin", "Operation Manager")
    ):
        return True

    emp_id = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name"
    )

    return (
        ptype == "create"
        or doc.employee == emp_id
        or doc.repoting_to == emp_id
    )


# --------------------------------------------------
# EMPLOYEE PERMISSIONS
# --------------------------------------------------

def get_employee_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if any(
        role in frappe.get_roles(user)
        for role in ("Administrator", "Admin", "Operation Manager")
    ):
        return None

    emp_id = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name"
    )

    return f"`tabEmployee`.name = '{emp_id}'" if emp_id else "1=0"


def has_employee_permission(doc, ptype, user):
    if any(
        role in frappe.get_roles(user)
        for role in ("Administrator", "Admin", "Operation Manager")
    ):
        return True

    emp_id = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name"
    )

    return doc.name == emp_id


# --------------------------------------------------
# ATTENDANCE PERMISSIONS
# --------------------------------------------------

def get_attendance_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if any(
        role in frappe.get_roles(user)
        for role in ("Administrator", "Admin", "Operation Manager")
    ):
        return None

    emp_id = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name"
    )

    return f"`tabAttendance`.employee = '{emp_id}'" if emp_id else "1=0"


def has_attendance_permission(doc, ptype, user):
    if any(
        role in frappe.get_roles(user)
        for role in ("Administrator", "Admin", "Operation Manager")
    ):
        return True

    emp_id = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name"
    )

    return doc.employee == emp_id
