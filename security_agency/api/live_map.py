import frappe

@frappe.whitelist()
def get_live_locations():
    """
    Latest location per employee with name + site
    """
    return frappe.db.sql("""
        SELECT
            ac.employee,
            emp.employee_name,
            emp.custom_site AS site,
            ac.latitude,
            ac.longitude,
            ac.checkin_time
        FROM `tabAutomatic Check In` ac
        INNER JOIN (
            SELECT employee, MAX(checkin_time) AS last_time
            FROM `tabAutomatic Check In`
            GROUP BY employee
        ) latest
            ON ac.employee = latest.employee
           AND ac.checkin_time = latest.last_time
        LEFT JOIN `tabEmployee` emp
            ON emp.name = ac.employee
        WHERE ac.latitude IS NOT NULL
          AND ac.longitude IS NOT NULL
    """, as_dict=True)
