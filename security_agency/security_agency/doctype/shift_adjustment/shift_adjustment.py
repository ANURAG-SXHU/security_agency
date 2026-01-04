# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt
# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate


class ShiftAdjustment(Document):

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    def validate(self):
        self.validate_assignments()

    def validate_assignments(self):
        if not self.shift_adjustment_assignment:
            frappe.throw(_("At least one replacement guard is required"))

        half_shift_count = 0
        guards = set()

        for row in self.shift_adjustment_assignment:
            if not row.replacement_guard:
                frappe.throw(_("Replacement Guard is mandatory"))

            if not row.shift_type:
                frappe.throw(_("Shift Type is mandatory"))

            if not frappe.db.exists("Shift Type", row.shift_type):
                frappe.throw(_("Invalid Shift Type: {0}").format(row.shift_type))

            if row.replacement_guard in guards:
                frappe.throw(_("Same guard cannot be added twice"))

            guards.add(row.replacement_guard)

            if row.is_half_shift:
                half_shift_count += 1

        if half_shift_count not in (0, 2):
            frappe.throw(
                _("Half shift requires exactly TWO guards"),
                title=_("Invalid Half Shift Setup")
            )

    # --------------------------------------------------
    # SUBMIT
    # --------------------------------------------------

    def on_submit(self):
        self.create_replacement_attendance()
        self.cancel_original_guard_attendance()

    # --------------------------------------------------
    # ATTENDANCE CREATION
    # --------------------------------------------------

    def create_replacement_attendance(self):
        attendance_date = getdate(self.date)

        for row in self.shift_adjustment_assignment:

            if frappe.db.exists(
                "Attendance",
                {
                    "employee": row.replacement_guard,
                    "attendance_date": attendance_date,
                    "docstatus": 1,
                }
            ):
                continue

            company = frappe.db.get_value(
                "Employee",
                row.replacement_guard,
                "company"
            )

            attendance_data = {
                "doctype": "Attendance",
                "employee": row.replacement_guard,
                "attendance_date": attendance_date,
                "company": company,
                "shift": row.shift_type,          # ✅ REQUIRED
                "custom_site": self.site,
                "shift_adjustment_ref": self.name
            }

            if row.is_half_shift:
                attendance_data.update({
                    "status": "Half Day",
                    "half_day_status": "Absent"
                })
            else:
                attendance_data["status"] = "Present"

            attendance = frappe.get_doc(attendance_data)
            attendance.insert(ignore_permissions=True)
            attendance.submit()

        frappe.msgprint(
            _("Attendance created for replacement guards"),
            indicator="green"
        )

    # --------------------------------------------------
    # ORIGINAL GUARD HANDLING
    # --------------------------------------------------

    def cancel_original_guard_attendance(self):
        """
        Cancel original guard attendance if exists
        """
        if not self.original_guard:
            return

        attendance_date = getdate(self.date)

        existing = frappe.db.get_all(
            "Attendance",
            filters={
                "employee": self.original_guard,
                "attendance_date": attendance_date,
                "docstatus": 1,
            },
            pluck="name"
        )

        for att in existing:
            doc = frappe.get_doc("Attendance", att)
            doc.cancel()
