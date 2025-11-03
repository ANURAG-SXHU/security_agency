import frappe
from frappe.utils import today, add_days

@frappe.whitelist()
def get_data():
    """
    Dashboard numbers and chart data for GPS Check-in Request.
    - Total, Pending, Approved, Rejected: only today's check-ins,
      validated against Deployment Sheet & Deployment Line.
    - Charts: last 7 days of check-ins for better visualisation.
    """

    today_start = today() + " 00:00:00"
    today_end = today() + " 23:59:59"
    week_ago = add_days(today(), -6)  # last 7 days including today

    # Total check-ins today
    total_today = frappe.db.count(
        "GPS Check-in Request",
        {"check_in_time": ["between", [today_start, today_end]]}
    )

    # Helper to count validated states for today
    def validated_count(pattern):
        return frappe.db.sql("""
            SELECT COUNT(*)
            FROM `tabGPS Check-in Request` g
            WHERE g.workflow_state LIKE %s
              AND g.check_in_time BETWEEN %s AND %s
              AND EXISTS (
                  SELECT 1
                  FROM `tabDeployment Sheet` s
                  INNER JOIN `tabDeployment Line` l ON l.parent = s.name
                  WHERE g.employee = l.guard
                    AND g.site = l.site
                    AND l.day = DAYNAME(g.check_in_time)
                    AND DATE(g.check_in_time) BETWEEN s.week_start_date AND s.week_end_date
              )
        """, (pattern, today_start, today_end))[0][0]

    pending = validated_count("Pending%")
    approved = validated_count("Approved%")
    rejected = validated_count("Rejected%")

    # Charts: show last 7 days of data
    by_site = frappe.db.sql("""
        SELECT IFNULL(site, 'No Site') as site, COUNT(*) as count
        FROM `tabGPS Check-in Request`
        WHERE check_in_time BETWEEN %s AND %s
        GROUP BY IFNULL(site, 'No Site')
    """, (week_ago, today_end), as_dict=True)

    last7 = frappe.db.sql("""
        SELECT DATE(check_in_time) as date, COUNT(*) as count
        FROM `tabGPS Check-in Request`
        WHERE check_in_time BETWEEN %s AND %s
        GROUP BY DATE(check_in_time)
        ORDER BY date
    """, (week_ago, today_end), as_dict=True)

    # Debugging: write to frappe.log so you can tail -f logs/frappe.log
    frappe.logger().info({"by_site": by_site, "last7": last7})

    return {
        "total_today": total_today,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "by_site": by_site,
        "last7": last7
    }
