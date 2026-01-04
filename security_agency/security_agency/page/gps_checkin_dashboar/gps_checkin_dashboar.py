import frappe
from frappe.utils import today, add_days

@frappe.whitelist()
def get_data(site=None, date=None):
    """
    Dashboard numbers and chart data for GPS Check-in Request.
    Now supports filters:
    - site (optional)
    - date (optional, default: today)
    """

    # --- Date Filter ---
    selected_date = date or today()
    day_start = selected_date + " 00:00:00"
    day_end = selected_date + " 23:59:59"

    # Last 7 days from selected date
    week_ago = add_days(selected_date, -6)

    # --- Dynamic WHERE conditions ---
    where_site = ""
    params_site = []

    if site:
        where_site = "AND g.site = %s"
        params_site.append(site)

    # --- Total Check-ins ---
    total_today = frappe.db.sql(
        f"""
        SELECT COUNT(*)
        FROM `tabGPS Check-in Request` g
        WHERE g.check_in_time BETWEEN %s AND %s
        {where_site}
        """,
        [day_start, day_end] + params_site
    )[0][0]

    # --- Validated Status Count ---
    def validated_count(pattern):
        return frappe.db.sql(
            f"""
            SELECT COUNT(*)
            FROM `tabGPS Check-in Request` g
            WHERE g.workflow_state LIKE %s
              AND g.check_in_time BETWEEN %s AND %s
              {where_site}
              AND EXISTS (
                  SELECT 1
                  FROM `tabDeployment Sheet` s
                  INNER JOIN `tabDeployment Line` l ON l.parent = s.name
                  WHERE g.employee = l.guard
                    AND g.site = l.site
                    AND l.day = DAYNAME(g.check_in_time)
                    AND DATE(g.check_in_time) BETWEEN s.week_start_date AND s.week_end_date
              )
            """,
            [pattern, day_start, day_end] + params_site
        )[0][0]

    pending = validated_count("Pending%")
    approved = validated_count("Approved%")
    rejected = validated_count("Rejected%")

    # --- Chart 1: By Site ---
    by_site = frappe.db.sql(
        f"""
        SELECT IFNULL(site, 'No Site') AS site, COUNT(*) AS count
        FROM `tabGPS Check-in Request` g
        WHERE g.check_in_time BETWEEN %s AND %s
        {where_site}
        GROUP BY IFNULL(site, 'No Site')
        """,
        [week_ago, day_end] + params_site,
        as_dict=True
    )

    # --- Chart 2: Last 7 Days ---
    last7 = frappe.db.sql(
        f"""
        SELECT DATE(g.check_in_time) AS date, COUNT(*) AS count
        FROM `tabGPS Check-in Request` g
        WHERE g.check_in_time BETWEEN %s AND %s
        {where_site}
        GROUP BY DATE(g.check_in_time)
        ORDER BY date
        """,
        [week_ago, day_end] + params_site,
        as_dict=True
    )

    # Debug log
    frappe.logger().info({
        "filters": {"site": site, "date": date},
        "by_site": by_site,
        "last7": last7
    })

    return {
        "total_today": total_today,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "by_site": by_site,
        "last7": last7
    }


@frappe.whitelist()
def get_sites():
    """Return list of sites for dropdown."""
    return frappe.db.get_all("Site", fields=["name"])
