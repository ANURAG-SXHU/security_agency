# # Copyright (c) 2025, Anurag Sahu
# # For license information, please see license.txt

# import frappe
# import fitz  # PyMuPDF
# import os
# import tempfile
# import json
# import re
# import pandas as pd
# import requests
# from frappe.model.document import Document
# from frappe.utils import today, cstr
# from openai import OpenAI, OpenAIError

# class WorkOrderBilling(Document):
#     def before_save(self):
#         if not self.upload_date:
#             self.upload_date = today()
#         if self.rate_per_day and self.total_present_days:
#             self.amount = float(self.rate_per_day) * int(self.total_present_days)

# def get_groq_client():
#     return OpenAI(
#         api_key=frappe.conf.get("groq_api_key"),
#         base_url="https://api.groq.com/openai/v1"
#     )

# @frappe.whitelist()
# def extract_work_order_info(name):
#     frappe.msgprint(f"⚙️ extract_work_order_info called for {name}")
#     doc = frappe.get_doc("Work Order Billing", name)

#     if not doc.work_order_pdf:
#         frappe.throw("Please attach the Work Order PDF.")

#     try:
#         # Fetch file
#         if doc.work_order_pdf.startswith("http://") or doc.work_order_pdf.startswith("https://"):
#             response = requests.get(doc.work_order_pdf)
#             if response.status_code != 200:
#                 frappe.throw("Failed to download the PDF from the provided URL.")
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
#                 tmp_file.write(response.content)
#                 pdf_path = tmp_file.name
#         else:
#             pdf_path = frappe.get_site_path("public", doc.work_order_pdf.replace("/files/", "files/"))

#         with fitz.open(pdf_path) as pdf:
#             text = "\n".join(page.get_text() for page in pdf)

#         prompt = f"""
# From the following work order document, extract the following fields and return them in JSON:
# - payment_due_date (format: YYYY-MM-DD)
# - rate_per_day (numeric)

# If a value is not found, use null.

# Document:
# {text[:5000]}
# """

#         client = get_groq_client()
#         response = client.chat.completions.create(
#             model="llama3-70b-8192",
#             messages=[{"role": "user", "content": prompt}]
#         )

#         result = response.choices[0].message.content or ""
#         json_match = re.search(r"\{[\s\S]+?\}", result)

#         if json_match:
#             try:
#                 values = json.loads(json_match.group(0))
#             except json.JSONDecodeError as e:
#                 frappe.log_error(str(e), "Invalid JSON from Groq")
#                 frappe.throw("⚠️ Couldn't parse AI response. Please verify the work order format.")

#             if values.get("payment_due_date"):
#                 doc.payment_due_date = values["payment_due_date"]
#             if values.get("rate_per_day"):
#                 doc.rate_per_day = float(values["rate_per_day"])

#             doc.save()
#             return "Work Order details extracted."
#         else:
#             frappe.throw("⚠️ No valid JSON found in AI response.")

#     except OpenAIError as e:
#         frappe.log_error(str(e), "Groq OpenAIError")
#         frappe.throw("⚠️ Groq API failed to respond correctly.")

#     finally:
#         if "pdf_path" in locals() and os.path.exists(pdf_path):
#             os.remove(pdf_path)

# @frappe.whitelist()
# def parse_attendance_xlsx(name):
#     frappe.msgprint(f"⚙️ parse_attendance_xlsx called for {name}")
#     doc = frappe.get_doc("Work Order Billing", name)

#     if not doc.attendance_xls:
#         frappe.throw("Please upload Attendance XLS file.")

#     file_path = frappe.get_site_path("public", doc.attendance_xls.replace("/files/", "files/"))
#     df = pd.read_excel(file_path)

#     required_columns = {"Employee Name", "Status"}
#     if not required_columns.issubset(set(df.columns)):
#         frappe.throw("Invalid attendance file. Required columns: 'Employee Name' and 'Status'.")

#     attendance_map = {}
#     for _, row in df.iterrows():
#         emp = cstr(row.get("Employee Name", "")).strip()
#         status = cstr(row.get("Status", "")).strip().lower()
#         if not emp:
#             continue
#         if emp not in attendance_map:
#             attendance_map[emp] = 0
#         if status == "present":
#             attendance_map[emp] += 1

#     total_days = 0
#     doc.set("guard_attendance_table", [])

#     for emp, days in attendance_map.items():
#         doc.append("guard_attendance_table", {
#             "employee_name": emp,
#             "present_days": days
#         })
#         total_days += days

#     doc.total_present_days = total_days

#     if doc.rate_per_day:
#         doc.amount = total_days * float(doc.rate_per_day)

#     doc.save()
#     return f"Uploaded {len(attendance_map)} guards' attendance."
import frappe
import fitz  # PyMuPDF
import os
import tempfile
import json
import re
import pandas as pd
import requests
from frappe.model.document import Document
from frappe.utils import today, cstr
from openai import OpenAI, OpenAIError

class WorkOrderBilling(Document):
    def before_save(self):
        if not self.upload_date:
            self.upload_date = today()
        if self.rate_per_day and self.total_present_days:
            self.amount = float(self.rate_per_day) * int(self.total_present_days)

def get_groq_client():
    return OpenAI(
        api_key=frappe.conf.get("groq_api_key"),
        base_url="https://api.groq.com/openai/v1"
    )

@frappe.whitelist()
def extract_work_order_info(name):
    frappe.msgprint(f"⚙️ extract_work_order_info called for {name}")
    doc = frappe.get_doc("Work Order Billing", name)

    if not doc.work_order_pdf:
        frappe.throw("Please attach the Work Order PDF.")

    try:
        # Download or resolve PDF path
        if doc.work_order_pdf.startswith("http://") or doc.work_order_pdf.startswith("https://"):
            response = requests.get(doc.work_order_pdf)
            if response.status_code != 200:
                frappe.throw("Failed to download the PDF from the provided URL.")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(response.content)
                pdf_path = tmp_file.name
        else:
            pdf_path = frappe.get_site_path("public", doc.work_order_pdf.replace("/files/", "files/"))

        with fitz.open(pdf_path) as pdf:
            text = "\n".join(page.get_text() for page in pdf)

        prompt = f"""
From the following work order document, extract the following fields and return them in JSON:
- payment_due_date (format: YYYY-MM-DD)
- rate_per_day (numeric)

If a value is not found, use null.

Document:
{text[:5000]}
"""

        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content or ""
        json_match = re.search(r"\{[\s\S]+?\}", result)

        if json_match:
            try:
                values = json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                frappe.log_error(str(e), "Invalid JSON from Groq")
                frappe.throw("⚠️ Couldn't parse AI response. Please verify the work order format.")

            if values.get("payment_due_date"):
                doc.payment_due_date = values["payment_due_date"]
            if values.get("rate_per_day"):
                doc.rate_per_day = float(values["rate_per_day"])

            doc.save()
            return "Work Order details extracted."
        else:
            frappe.throw("⚠️ No valid JSON found in AI response.")

    except OpenAIError as e:
        frappe.log_error(str(e), "Groq OpenAIError")
        frappe.throw("⚠️ Groq API failed to respond correctly.")

    finally:
        if "pdf_path" in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)

@frappe.whitelist()
def parse_attendance_xlsx(name):
    frappe.msgprint(f"⚙️ parse_attendance_xlsx called for {name}")
    doc = frappe.get_doc("Work Order Billing", name)

    if not doc.attendance_xls:
        frappe.throw("Please upload Attendance XLS file.")

    file_path = frappe.get_site_path("public", doc.attendance_xls.replace("/files/", "files/"))
    df = pd.read_excel(file_path)

    required_columns = {"Employee Name", "Status"}
    if not required_columns.issubset(set(df.columns)):
        frappe.throw("Invalid attendance file. Required columns: 'Employee Name' and 'Status'.")

    attendance_map = {}
    for _, row in df.iterrows():
        emp = cstr(row.get("Employee Name", "")).strip()
        status = cstr(row.get("Status", "")).strip().lower()
        if not emp:
            continue
        if emp not in attendance_map:
            attendance_map[emp] = 0
        if status == "present":
            attendance_map[emp] += 1

    total_days = 0
    doc.set("guard_attendance_table", [])

    for emp, days in attendance_map.items():
        doc.append("guard_attendance_table", {
            "employee_name": emp,
            "present_days": days
        })
        total_days += days

    doc.total_present_days = total_days

    if doc.rate_per_day:
        doc.amount = total_days * float(doc.rate_per_day)

    doc.save()
    return f"Uploaded {len(attendance_map)} guards' attendance."
