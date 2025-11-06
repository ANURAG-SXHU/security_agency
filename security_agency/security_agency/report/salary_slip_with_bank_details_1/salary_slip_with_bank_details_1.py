# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe

# def execute(filters=None):
#     month = filters.get("month")
#     year = filters.get("year")

#     columns = [
#         {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
#         {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
#         {"label": "Bank Account No", "fieldname": "bank_ac_no", "fieldtype": "Data", "width": 150},
#         {"label": "Bank Branch", "fieldname": "custom_bank_branch", "fieldtype": "Data", "width": 150},
#         {"label": "IFSC Code", "fieldname": "ifsc_code", "fieldtype": "Data", "width": 120},
#         {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 120}
#     ]

#     data = frappe.db.sql("""
#         SELECT 
#             ss.employee,
#             ss.employee_name,
#             e.bank_ac_no,
#             e.custom_bank_branch,
#             e.ifsc_code,
#             ss.net_pay
#         FROM 
#             `tabSalary Slip` ss
#         LEFT JOIN 
#             `tabEmployee` e ON ss.employee = e.name
#         WHERE 
#             ss.docstatus = 1
#             AND MONTH(ss.start_date) = MONTH(STR_TO_DATE(%(month)s, '%%M'))
#             AND YEAR(ss.start_date) = %(year)s
#     """, filters, as_dict=True)

#     return columns, data
def execute(filters=None):
    filters = filters or {}

    conditions = ""
    values = {}

    if filters.get("month") and filters.get("year"):
        conditions += " AND MONTH(ss.start_date) = %(month)s AND YEAR(ss.start_date) = %(year)s"
        values.update({
            "month": frappe.utils.getdate("2025-" + filters.month + "-01").month if not str(filters.month).isdigit() else filters.month,
            "year": filters.year
        })

    if filters.get("site"):
        conditions += " AND e.custom_site = %(site)s"
        values["site"] = filters.site

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Bank Account No", "fieldname": "bank_ac_no", "fieldtype": "Data", "width": 150},
        {"label": "Bank Branch", "fieldname": "custom_bank_branch", "fieldtype": "Data", "width": 150},
        {"label": "IFSC Code", "fieldname": "ifsc_code", "fieldtype": "Data", "width": 120},
        {"label": "Site", "fieldname": "custom_site", "fieldtype": "Link", "options": "Site", "width": 120},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 120}
    ]

    data = frappe.db.sql(f"""
        SELECT 
            ss.employee,
            ss.employee_name,
            e.bank_ac_no,
            e.custom_bank_branch,
            e.ifsc_code,
            e.custom_site,
            ss.net_pay
        FROM 
            `tabSalary Slip` ss
        LEFT JOIN 
            `tabEmployee` e ON ss.employee = e.name
        WHERE 
            ss.docstatus = 1 {conditions}
    """, values, as_dict=True)

    return columns, data

