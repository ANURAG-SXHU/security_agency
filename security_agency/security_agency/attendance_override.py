import frappe
from hrms.hr.doctype.attendance.attendance import Attendance as HRMSAttendance


class CustomAttendance(HRMSAttendance):
    """Override HRMS Attendance validation to allow half-shift overlaps."""

    def validate_overlapping_shift_attendance(self):
        """Completely skip overlap validation if this is a half-shift."""
        if not self.shift:
            # No shift assigned → fall back to HRMS validation
            super().validate_overlapping_shift_attendance()
            return

        # Get half_shift flag
        current_half = frappe.db.get_value("Shift Type", self.shift, "half_shift") or 0

        if int(current_half) == 1:
            # ✅ Skip HRMS overlap validation entirely
            frappe.logger().info(
                f"🚀 CustomAttendance active — skipping overlap validation for half-shift: {self.shift}"
            )
            return  # stop here, don’t call parent!

        # For normal (full) shifts, use HRMS default validation
        super().validate_overlapping_shift_attendance()
