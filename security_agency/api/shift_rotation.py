import frappe
from frappe.utils import getdate


# --------------------------------------------------
# CHECK IF ROTATION EXISTS
# --------------------------------------------------

def rotation_exists(site, guard, check_in_time):
    """
    Check whether a valid Guard Shift Rotation exists
    for the given site, guard and date.
    """
    if not site or not guard or not check_in_time:
        return False

    check_date = getdate(check_in_time)
    day_name = check_date.strftime("%A")

    return bool(
        frappe.db.exists(
            "Guard Shift Rotation",
            {
                "site": site,
                "guard": guard,
                "day_of_week": day_name,
                "rotation_start_date": ["<=", check_date],
            }
        )
    )


# --------------------------------------------------
# RESOLVE PLANNED SHIFT
# --------------------------------------------------

def resolve_planned_shift(site, guard, check_in_time):
    """
    Resolve planned shift for a guard on a given date
    using Guard Shift Rotation.
    """
    if not site or not guard or not check_in_time:
        return None

    check_date = getdate(check_in_time)
    day_name = check_date.strftime("%A")

    # Fetch rotation
    rotation = frappe.get_value(
        "Guard Shift Rotation",
        {
            "site": site,
            "guard": guard,
            "day_of_week": day_name,
            "rotation_start_date": ["<=", check_date],
        },
        ["name", "rotation_start_date"],
        as_dict=True,
    )

    if not rotation:
        return None

    rotation_doc = frappe.get_doc("Guard Shift Rotation", rotation.name)

    # ✅ CORRECT CHILD TABLE FIELDNAME
    if not rotation_doc.guard_shift_rotation_item:
        return None

    # Sort by order
    sequence = sorted(
        rotation_doc.guard_shift_rotation_item,
        key=lambda r: r.order or 0
    )

    start_date = getdate(rotation.rotation_start_date)
    days_diff = (check_date - start_date).days
    week_index = days_diff // 7

    index = week_index % len(sequence)

    return sequence[index].shift_type
