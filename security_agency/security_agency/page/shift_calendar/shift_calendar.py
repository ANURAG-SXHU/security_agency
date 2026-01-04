import frappe
from frappe.utils import getdate, add_days
from datetime import date
import calendar


@frappe.whitelist()
def get_shift_calendar(site, month):
    """
    Generate planned shift calendar (NO attendance)
    Based on Guard Shift Rotation
    """

    if not site or not month:
        return []

    month_date = getdate(month)
    year = month_date.year
    month_num = month_date.month

    last_day = calendar.monthrange(year, month_num)[1]

    start_date = date(year, month_num, 1)
    end_date = date(year, month_num, last_day)

    rotations = frappe.get_all(
        "Guard Shift Rotation",
        filters={"site": site},
        fields=[
            "name",
            "guard",
            "day_of_week",
            "rotation_start_date"
        ]
    )

    results = []

    for rot in rotations:
        rot_doc = frappe.get_doc("Guard Shift Rotation", rot.name)

        # ✅ CORRECT child table
        if not rot_doc.guard_shift_rotation_item:
            continue

        sequence = sorted(
            rot_doc.guard_shift_rotation_item,
            key=lambda r: r.order
        )

        d = start_date
        while d <= end_date:

            # Match weekday
            if d.strftime("%A") != rot.day_of_week:
                d = add_days(d, 1)
                continue

            # Rotation must start after rotation_start_date
            if d < rot.rotation_start_date:
                d = add_days(d, 1)
                continue

            weeks_passed = ((d - rot.rotation_start_date).days) // 7
            index = weeks_passed % len(sequence)

            shift = sequence[index].shift_type

            guard_name = frappe.db.get_value(
                "Employee",
                rot.guard,
                "employee_name"
            )

            results.append({
                "guard": guard_name,
                "date": str(d),
                "shift": shift
            })

            d = add_days(d, 7)

    return results
