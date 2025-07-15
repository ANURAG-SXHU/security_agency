import frappe
from frappe.utils import getdate, nowdate, add_days

def execute():
    today = getdate(nowdate())
    weekday = today.strftime('%A')

    frappe.logger().info(f"🔍 Attendance Anomaly Check started for {today} ({weekday})")

    # Get all Deployment Sheets covering today
    deployments = frappe.get_all(
        "Deployment Sheet",
        filters={"week_start_date": ["<=", today]},
        fields=["name", "week_start_date"]
    )

    for dep in deployments:
        week_start = dep.week_start_date
        week_end = add_days(week_start, 6)

        # Get planned deployments for this weekday
        lines = frappe.get_all(
            "Deployment Line",
            filters={
                "parent": dep.name,
                "day": weekday
            },
            fields=["site", "guard"]
        )

        if not lines:
            frappe.logger().info(f"➡️ No deployment lines for {dep.name} on {weekday}")
            continue

        # Group guards by site
        site_guards = {}
        for line in lines:
            site_guards.setdefault(line.site, []).append(line.guard)

        for site, guards in site_guards.items():
            # Who checked in today?
            checkins = frappe.get_all(
                "GPS Check-in Request",
                filters={
                    "site": site,
                    "employee": ["in", guards],
                    "check_in_time": ["between", [today, add_days(today, 1)]]
                },
                fields=["employee"]
            )
            present_guards = {c.employee for c in checkins}
            absent_guards = set(guards) - present_guards

            if len(absent_guards) >= 3:
                # Flag only if not already flagged
                if not frappe.db.exists("Attendance Anomaly", {
                    "site": site,
                    "date": today,
                    "type": "Site Anomaly"
                }):
                    anomaly_doc = frappe.get_doc({
                        "doctype": "Attendance Anomaly",
                        "site": site,
                        "date": today,
                        "absentee_count": len(absent_guards),
                        "type": "Site Anomaly",
                        "notes": f"3+ absentees: {', '.join(absent_guards)}"
                    })
                    anomaly_doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.logger().info(f"🚩 Flagged site {site}: {len(absent_guards)} absentees")

        # Check for guards with NO check-ins all week
        unique_guards = {line.guard for line in lines}
        for guard in unique_guards:
            weekly_checkins = frappe.get_all(
                "GPS Check-in Request",
                filters={
                    "employee": guard,
                    "check_in_time": ["between", [week_start, week_end]]
                },
                fields=["name"]
            )
            if not weekly_checkins:
                if not frappe.db.exists("Attendance Anomaly", {
                    "guard": guard,
                    "date": today,
                    "type": "No Check-ins"
                }):
                    anomaly_doc = frappe.get_doc({
                        "doctype": "Attendance Anomaly",
                        "guard": guard,
                        "date": today,
                        "type": "No Check-ins",
                        "notes": f"No GPS check-ins found for {guard} for week {week_start} to {week_end}."
                    })
                    anomaly_doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.logger().info(f"🚩 Flagged guard {guard}: No check-ins this week")

    frappe.logger().info("✅ Attendance Anomaly Check completed.")
