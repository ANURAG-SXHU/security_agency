import frappe
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day, now_datetime


class BulkSiteSalarySlipTool(Document):
    """
    Bulk Site Salary Slip Tool:
      - Auto-fills current month and year every time the form is opened
      - Provides methods to get guards and create+submit salary slips
    """

    def onload(self):
        current = now_datetime()
        self.month = current.strftime("%B")
        self.year = current.strftime("%Y")
        print(f"[DEBUG] onload: month set to {self.month}, year set to {self.year}")


@frappe.whitelist()
def get_current_month_year():
    current = now_datetime()
    print(f"[DEBUG] get_current_month_year: {current}")
    return {"month": current.strftime("%B"), "year": current.strftime("%Y")}


@frappe.whitelist()
def get_guards(site):
    print(f"[DEBUG] get_guards called with site: {site}")

    guards = frappe.get_all(
        "Employee",
        filters={
            "custom_site": site,
            "status": "Active",
            "designation": "Guard"
        },
        fields=["name as employee", "employee_name"]
    )

    print(f"[DEBUG] get_guards found {len(guards)} guard(s): {guards}")
    return guards


@frappe.whitelist()
def create_salary_slips(docname):
    """
    Create and submit salary slips for every guard in the child table.
    Sends realtime progress updates for the frontend progress bar.
    """
    print(f"[DEBUG] create_salary_slips called for document: {docname}")
    doc = frappe.get_doc("Bulk Site Salary Slip Tool", docname)

    print(f"[DEBUG] Selected site: {doc.site}, month: {doc.month}, year: {doc.year}")

    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    month_num = month_map.get(doc.month)
    if not month_num:
        frappe.throw("Invalid month selected")

    year = int(doc.year)
    start_date = get_first_day(f"{year}-{month_num:02d}-01")
    end_date = get_last_day(start_date)
    print(f"[DEBUG] Computed payroll period: {start_date} to {end_date}")

    total = len(doc.bulk_site_salary_slip_employee)
    created_slips = []
    processed = 0

    for row in doc.bulk_site_salary_slip_employee:
        processed += 1
        # Send realtime progress to the frontend
        frappe.publish_realtime(
            "bulk_salary_progress",
            {"current": processed, "total": total},
            user=frappe.session.user
        )

        print(f"[DEBUG] Processing employee: {row.employee} - {row.employee_name}")
        emp = frappe.db.get_value(
            "Employee",
            row.employee,
            ["designation", "custom_site"],
            as_dict=True
        )

        if not emp:
            print(f"[DEBUG] Employee record not found: {row.employee}")
            continue

        if emp.designation != "Guard":
            print(f"[DEBUG] Skipped {row.employee}: designation is {emp.designation}")
            continue

        if emp.custom_site != doc.site:
            print(f"[DEBUG] Skipped {row.employee}: custom_site mismatch ({emp.custom_site} != {doc.site})")
            continue

        exists = frappe.db.exists(
            "Salary Slip",
            {
                "employee": row.employee,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        print(f"[DEBUG] Existing salary slip for {row.employee}: {exists}")
        if exists:
            continue

        # Create and submit salary slip
        ss = frappe.new_doc("Salary Slip")
        ss.employee = row.employee
        ss.start_date = start_date
        ss.end_date = end_date
        ss.payroll_frequency = "Monthly"
        ss.posting_date = end_date
        ss.save(ignore_permissions=True)

        # ✅ Auto-submit the salary slip
        ss.submit()
        print(f"[DEBUG] Created and submitted salary slip: {ss.name}")

        created_slips.append(ss.name)

    # Ensure final progress is shown as complete
    frappe.publish_realtime(
        "bulk_salary_progress",
        {"current": total, "total": total, "done": True},
        user=frappe.session.user
    )

    print(f"[DEBUG] Total salary slips created and submitted: {len(created_slips)}")
    return {
        "message": f"{len(created_slips)} salary slips created and submitted for Guards at site {doc.site}.",
        "slips": created_slips
    }
