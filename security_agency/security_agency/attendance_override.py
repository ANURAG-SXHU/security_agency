import frappe
from hrms.hr.doctype.attendance.attendance import Attendance as HRMSAttendance


class CustomAttendance(HRMSAttendance):
    """Override HRMS Attendance validation to allow half-shift overlaps."""

    def validate_overlapping_shift_attendance(self):
        """
        Custom override:
        - Skip overlap validation if this attendance belongs to a half-shift type.
        - Use HRMS logic for all other (full) shifts.
        """

        # 🧩 Step 1: If no shift is linked, fallback to HRMS default logic
        if not self.shift:
            frappe.logger().info(
                f"⚙️ No shift assigned for attendance {self.name or '[unsaved]'}, using default HRMS validation."
            )
            super().validate_overlapping_shift_attendance()
            return

        # 🧩 Step 2: Check if 'half_shift' field exists in Shift Type table
        current_half = 0
        if frappe.db.has_column("Shift Type", "custom_half_shift"):
            current_half = frappe.db.get_value("Shift Type", self.shift, "custom_half_shift") or 0
        else:
            frappe.logger().warning(
                f"⚠️ 'half_shift' column missing in Shift Type DocType. Consider adding it for half-day logic."
            )

        # 🧩 Step 3: Apply half-shift skip logic
        if int(current_half) == 1:
            frappe.logger().info(
                f"🚀 CustomAttendance active — skipping overlap validation for half-shift: {self.shift}"
            )
            return  # ✅ Skip overlap validation entirely for half-shift

        # 🧩 Step 4: Default behavior for normal shifts
        frappe.logger().info(
            f"✅ Performing HRMS overlap validation for full-shift: {self.shift}"
        )
        super().validate_overlapping_shift_attendance()


# --- Optional: Register override globally if not already in hooks.py ---
override_doctype_class = {
    "Attendance": "security_agency.security_agency.attendance_override.CustomAttendance"
}
