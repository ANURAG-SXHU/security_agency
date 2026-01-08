import frappe
from frappe.utils import getdate, add_days
from datetime import date
import calendar
from frappe.utils.xlsxutils import make_xlsx


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

        # Skip if no rotation items
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

@frappe.whitelist()
def export_shift_calendar_excel(site, month):
    import calendar
    from datetime import datetime
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    from frappe.utils import getdate

    if not site or not month:
        frappe.throw("Site and Month are required")

    data = get_shift_calendar(site, month)
    if not data:
        frappe.throw("No data found")

    month_date = getdate(month)
    year = month_date.year
    month_num = month_date.month

    wb = Workbook()
    ws = wb.active
    ws.title = "Shift Calendar"

    # ---------------- STYLES ----------------
    header_fill = PatternFill("solid", fgColor="DDDDDD")
    header_font = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    shift_fills = {
        "A SHIFT": PatternFill("solid", fgColor="C6EFCE"),  # green
        "B SHIFT": PatternFill("solid", fgColor="BDD7EE"),  # blue
        "C SHIFT": PatternFill("solid", fgColor="E4D7F5")   # purple
    }

    # ---------------- TITLE ----------------
    title = f"Shift Calendar - {site} ({month_date.strftime('%B %Y')})"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=14)
    ws.cell(row=1, column=1).alignment = center

    # ---------------- HEADERS ----------------
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for col, day in enumerate(days, start=1):
        cell = ws.cell(row=3, column=col, value=day)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        ws.column_dimensions[chr(64 + col)].width = 22

    # ---------------- BUILD CALENDAR ----------------
    cal = calendar.monthcalendar(year, month_num)
    start_row = 4

    # Group data by date
    data_map = {}
    for r in data:
        data_map.setdefault(r["date"], []).append(r)

    for week in cal:
        for col, day in enumerate(week, start=1):
            cell = ws.cell(row=start_row, column=col)
            cell.alignment = center

            if day == 0:
                continue

            date_str = f"{year}-{month_num:02d}-{day:02d}"
            cell.value = str(day)

            if date_str in data_map:
                lines = []
                for r in data_map[date_str]:
                    lines.append(f'{r["guard"]} ({r["shift"]})')

                    for shift, fill in shift_fills.items():
                        if shift in r["shift"]:
                            cell.fill = fill

                cell.value = f"{day}\n" + "\n".join(lines)

        start_row += 1

    # ---------------- EXPORT RESPONSE ----------------
    from io import BytesIO
    file_stream = BytesIO()
    wb.save(file_stream)

    frappe.response["filename"] = f"Shift_Calendar_{site}_{month}.xlsx"
    frappe.response["filecontent"] = file_stream.getvalue()
    frappe.response["type"] = "binary"
