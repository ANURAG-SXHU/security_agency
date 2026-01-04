# import frappe
# from frappe.model.document import Document
# from frappe.utils import get_datetime, formatdate, now_datetime, nowdate
# from frappe import _
# from datetime import datetime


# class GPSCheckinRequest(Document):
#     def before_save(self):
#         if self.shift_type:
#             return

#         # Safely convert string to datetime
#         check_in_dt = get_datetime(self.check_in_time)
#         weekday = check_in_dt.strftime("%A")
#         check_in_time_only = check_in_dt.time()

#         # Find Deployment Sheet for the given week
#         sheet = frappe.db.get_value(
#             "Deployment Sheet",
#             {
#                 "week_start_date": ["<=", check_in_dt.date()],
#                 "week_end_date": [">=", check_in_dt.date()],
#             },
#             "name"
#         )
#         if not sheet:
#             frappe.throw(_("No Deployment Sheet found for this week."))

#         # ✅ Fetch ALL Deployment Lines for this guard, site, and day
#         deployment_lines = frappe.get_all(
#             "Deployment Line",
#             filters={
#                 "parent": sheet,
#                 "guard": self.employee,
#                 "site": self.site,
#                 "day": weekday
#             },
#             fields=["shift"]
#         )

#         if not deployment_lines:
#             frappe.throw(_("No Deployment Line found for this guard/site/day."))

#         matched_shift = None

#         # ✅ Loop through all possible shifts to find a valid one
#         for line in deployment_lines:
#             shift = frappe.get_doc("Shift Type", line.shift)
#             shift_start = datetime.strptime(str(shift.start_time), "%H:%M:%S").time()
#             shift_end = datetime.strptime(str(shift.end_time), "%H:%M:%S").time()

#             # Handle overnight shifts (where end time is past midnight)
#             if shift_start < shift_end:
#                 valid = shift_start <= check_in_time_only <= shift_end
#             else:
#                 valid = check_in_time_only >= shift_start or check_in_time_only <= shift_end

#             if valid:
#                 matched_shift = line.shift
#                 break  # ✅ stop at first valid shift match

#         if not matched_shift:
#             frappe.throw(_("Check-in time does not fall within any assigned shift."))

#         self.shift_type = matched_shift

#         if self.upload_selfie:
#             make_public(self.upload_selfie)

#     # def autoname(self):
#     #     if not self.check_in_time:
#     #         self.check_in_time = now_datetime()

#     #     date_str = formatdate(self.check_in_time, "yyyyMMdd")
#     #     emp_name = frappe.db.get_value("Employee", self.employee, "employee_name") or "UNKNOWN"
#     #     self.name = f"{emp_name.replace(' ', '').upper()}-{date_str}"
#     def autoname(self):
#         if not self.check_in_time:
#             self.check_in_time = now_datetime()

#         date_str = formatdate(self.check_in_time, "yyyyMMdd")
#         emp_name = frappe.db.get_value("Employee", self.employee, "employee_name") or "UNKNOWN"
#         base_name = f"{emp_name.replace(' ', '').upper()}-{date_str}"

#         # Get existing records for the same employee and date
#         existing = frappe.db.sql(
#             """SELECT name FROM `tabGPS Check-in Request`
#             WHERE name LIKE %s ORDER BY creation DESC""",
#             (f"{base_name}-%",),
#         )

#         # Determine sequence number
#         seq = len(existing) + 1
#         seq_str = str(seq).zfill(3)  # Pads with zeros (001, 002, 003...)

#         # Final name
#         self.name = f"{base_name}-{seq_str}"

#     def before_insert(self):
#         self.workflow_state = "Draft"

#     def on_update_after_submit(self):
#         if self.workflow_state in ["Approved(Guard)", "Approved(Supervisor)"]:
#             if not self.employee:
#                 frappe.msgprint("❌ Employee is missing. Cannot create attendance.")
#                 return

#             create_attendance_for_employee(
#                 employee_id=self.employee,
#                 attendance_datetime=self.check_in_time or now_datetime(),
#                 ref_doctype=self.doctype,
#                 ref_name=self.name
#             )
#             frappe.msgprint("✅ Attendance created.")


# # ------------------------
# # Attendance Creation Logic
# # ------------------------

# # @frappe.whitelist()
# # def create_attendance_for_employee(
# #     employee_id,
# #     attendance_date=None,
# #     status='Present',
# #     ref_doctype=None,
# #     ref_name=None,
# #     attendance_datetime=None
# # ):
# #     if not attendance_date:
# #         attendance_date = nowdate()

# #     # Fetch shift from the referenced GPS Check-in Request
# #     shift = None
# #     if ref_doctype == "GPS Check-in Request" and ref_name:
# #         shift = frappe.db.get_value("GPS Check-in Request", ref_name, "shift_type")

# #     if not shift:
# #         frappe.msgprint("⚠️ Shift not found. Cannot check for duplicates.")
# #         return

# #     # Check if attendance already exists for the same employee, date, and shift
# #     exists = frappe.db.exists("Attendance", {
# #         "employee": employee_id,
# #         "attendance_date": attendance_date,
# #         "shift": shift,
# #         "docstatus": 1
# #     })

# #     if exists:
# #         frappe.msgprint(f"ℹ️ Attendance already exists for {employee_id} on {attendance_date} for shift {shift}.")
# #         return

# #     # Create Attendance document
# #     attendance = frappe.get_doc({
# #         "doctype": "Attendance",
# #         "employee": employee_id,
# #         "attendance_date": attendance_date,
# #         "status": status,
# #         "shift": shift,
# #         "company": frappe.db.get_value("Employee", employee_id, "company"),
# #         "gps_checkin_ref": ref_name if ref_doctype == "GPS Check-in Request" else None,
# #         "check_in_by": frappe.session.user,
# #         "in_time": attendance_datetime or now_datetime()
# #     })

# #     # ✅ Bypass permission check since this is system-driven
# #     attendance.insert(ignore_permissions=True)
# #     attendance.submit()

# #     frappe.msgprint(f"✅ Attendance submitted for {employee_id} on {attendance_date} for shift {shift}.")
# @frappe.whitelist()
# def create_attendance_for_employee(
#     employee_id,
#     attendance_date=None,
#     status='Present',
#     ref_doctype=None,
#     ref_name=None,
#     attendance_datetime=None
# ):
#     from frappe.utils import nowdate, now_datetime

#     if not attendance_date:
#         attendance_date = nowdate()

#     # Fetch shift and site from the referenced GPS Check-in Request
#     shift, site = None, None
#     if ref_doctype == "GPS Check-in Request" and ref_name:
#         shift, site = frappe.db.get_value(
#             "GPS Check-in Request", ref_name, ["shift_type", "site"]
#         )

#     if not shift:
#         frappe.msgprint("⚠️ Shift not found. Cannot check for duplicates.")
#         return

#     # Check if attendance already exists for the same employee, date, and shift
#     exists = frappe.db.exists("Attendance", {
#         "employee": employee_id,
#         "attendance_date": attendance_date,
#         "shift": shift,
#         "docstatus": 1
#     })

#     if exists:
#         frappe.msgprint(f"ℹ️ Attendance already exists for {employee_id} on {attendance_date} for shift {shift}.")
#         return

#     # Fetch company from Employee
#     company = frappe.db.get_value("Employee", employee_id, "company")

#     # Create Attendance document with new field name `custom_site`
#     attendance = frappe.get_doc({
#         "doctype": "Attendance",
#         "employee": employee_id,
#         "attendance_date": attendance_date,
#         "status": status,
#         "shift": shift,
#         "custom_site": site,  # ✅ updated field name
#         "company": company,
#         "gps_checkin_ref": ref_name if ref_doctype == "GPS Check-in Request" else None,
#         "check_in_by": frappe.session.user,
#         "in_time": attendance_datetime or now_datetime()
#     })

#     # ✅ Bypass permission check since this is system-driven
#     attendance.insert(ignore_permissions=True)
#     attendance.submit()

#     frappe.msgprint(
#         f"✅ Attendance submitted for {employee_id} on {attendance_date} for shift {shift} (Site: {site or 'N/A'})."
#     )



# # # ------------------------
# # # GPS Check-in Request Permissions
# # # ------------------------
# def get_permission_query_conditions(user):
#     if not user:
#         user = frappe.session.user

#     # ✅ Check roles correctly
#     if any(role in frappe.get_roles(user) for role in ["Administrator", "Admin", "Operation Manager"]):
#         return None

#     emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
#     if not emp_id:
#         return "1=0"

#     return (
#         f"`tabGPS Check-in Request`.employee = '{emp_id}' "
#         f"OR `tabGPS Check-in Request`.repoting_to = '{emp_id}'"
#     )


# def has_permission(doc, ptype, user):
#     # ✅ Check roles correctly
#     if any(role in frappe.get_roles(user) for role in ["Administrator", "Admin", "Operation Manager"]):
#         return True

#     emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

#     if ptype == "create":
#         return True

#     return doc.employee == emp_id or doc.repoting_to == emp_id



# # ------------------------
# # Employee Permissions
# # ------------------------

# def get_employee_permission_query_conditions(user):
#     if not user:
#         user = frappe.session.user

#     # ✅ Check roles correctly
#     if "Administrator" in frappe.get_roles(user) or "Admin" in frappe.get_roles(user) or "Operation Manager" in frappe.get_roles(user):
#         return None  # Allow full access

#     emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
#     return f"`tabEmployee`.name = '{emp_id}'" if emp_id else "1=0"


# def has_employee_permission(doc, ptype, user):
#     # ✅ Check roles correctly
#     if "Administrator" in frappe.get_roles(user) or "Admin" in frappe.get_roles(user) or "Operation Manager" in frappe.get_roles(user):
#         return True  # Allow document access

#     emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
#     return doc.name == emp_id

# # ------------------------
# # Attendance Permissions
# # ------------------------

# def get_attendance_permission_query_conditions(user):
#     if not user:
#         user = frappe.session.user
#     if user in ["Administrator", "Admin", "Operation Manager"]:
#         return None

#     emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
#     return f"`tabAttendance`.employee = '{emp_id}'" if emp_id else "1=0"


# def has_attendance_permission(doc, ptype, user):
#     if user in ["Administrator", "Admin", "Operation Manager"]:
#         return True

#     emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

#     # Only allow the employee to see their own attendance
#     return doc.employee == emp_id



# @frappe.whitelist()
# def make_public(file_url):
#     """
#     Ensure a file is stored as public in /public/files
#     even if uploaded as private.
#     """
#     f = frappe.get_doc("File", {"file_url": file_url})
#     if f.is_private:
#         f.is_private = 0
#         f.save(ignore_permissions=True)
#         frappe.db.commit()
#     return True
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
