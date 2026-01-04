import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def get_guard_attendance_summary(date=None):
    if not date:
        date = nowdate()

    # Get assigned guards from Deployment Line
    deployment_lines = frappe.get_all("Deployment Line",
        fields=["employee", "parent"],
        filters={"parenttype": "Deployment Sheet"})

    # Map site to guards
    site_map = {}
    for line in deployment_lines:
        site = frappe.db.get_value("Deployment Sheet", line.parent, "site")
        if site not in site_map:
            site_map[site] = {"assigned": set(), "present": set()}
        site_map[site]["assigned"].add(line.employee)

    # Get check-ins today
    checkins = frappe.get_all("GPS Check-in Request",
        fields=["employee", "site"],
        filters={"check_in_time": [">=", f"{date} 00:00:00"]})

    for check in checkins:
        if check.site in site_map and check.employee in site_map[check.site]["assigned"]:
            site_map[check.site]["present"].add(check.employee)

    # Final summary
    summary = []
    for site, data in site_map.items():
        assigned = data["assigned"]
        present = data["present"]
        absent = assigned - present
        summary.append({
            "site": site,
            "assigned": len(assigned),
            "present": len(present),
            "absent": len(absent),
            "absent_employees": list(absent)
        })

    return summary
