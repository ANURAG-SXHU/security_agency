# # Copyright (c) 2025, Anurag Sahu and contributors
# # For license information, please see license.txt

# import frappe
# from frappe.model.document import Document
# import fitz  # PyMuPDF
# import os
# import requests
# import tempfile
# import re
# from frappe.utils import today
# from openai import OpenAI, OpenAIError


# class Tender(Document):
#     def before_save(self):
#         if not self.upload_date:
#             self.upload_date = today()


# def get_groq_client():
#     return OpenAI(
#         api_key=frappe.conf.get("groq_api_key"),
#         base_url="https://api.groq.com/openai/v1"
#     )


# @frappe.whitelist()
# def extract_summary(name):
#     doc = frappe.get_doc("Tender", name)

#     if not doc.tender_pdf:
#         frappe.throw("Please attach or link a Tender PDF.")

#     # Handle file: remote or uploaded
#     if doc.tender_pdf.startswith("http://") or doc.tender_pdf.startswith("https://"):
#         response = requests.get(doc.tender_pdf)
#         if response.status_code != 200:
#             frappe.throw("Failed to download the PDF from the provided URL.")
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
#             tmp_file.write(response.content)
#             tmp_file_path = tmp_file.name
#         pdf_path = tmp_file_path
#     else:
#         pdf_path = frappe.get_site_path("public", doc.tender_pdf.replace("/files/", "files/"))

#     with fitz.open(pdf_path) as pdf:
#         text = "\n".join(page.get_text() for page in pdf)

#     # Groq prompt
#     prompt = f"""
# From the following tender document, extract:
# 1. Scope of Work
# 2. Eligibility Criteria
# 3. Required Documents
# 4. Submission Date (YYYY-MM-DD format)
# 5. EMD Deadline (YYYY-MM-DD format)
# 6. Pre-bid Meeting Date (YYYY-MM-DD format)

# Tender Text:
# {text[:6000]}
# """

#     try:
#         client = get_groq_client()
#         response = client.chat.completions.create(
#             model="llama3-70b-8192",
#             messages=[{"role": "user", "content": prompt}]
#         )

#         result = response.choices[0].message.content

#         # ✂️ Parse sections
#         doc.scope_of_work = result.split("Eligibility")[0].strip()

#         if "Eligibility" in result and "Required" in result:
#             doc.eligibility_criteria = result.split("Eligibility")[1].split("Required")[0].strip()
#             doc.required_documents = result.split("Required")[1].split("Submission Date")[0].strip()

#         # 📅 Extract dates
#         date_fields = {
#             "submission_date": r"Submission Date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
#             "emd_deadline": r"EMD Deadline\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
#             "pre_bid_date": r"Pre-bid Meeting Date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})"
#         }

#         for field, pattern in date_fields.items():
#             match = re.search(pattern, result)
#             if match:
#                 setattr(doc, field, match.group(1))

#         doc.save()

#     except OpenAIError as e:
#         frappe.throw(f"Groq API error: {e}")

#     finally:
#         if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
#             os.remove(tmp_file_path)

#     return "Summary and dates extracted successfully."


# @frappe.whitelist()
# def ask_ai_for_rate(name):
#     doc = frappe.get_doc("Tender", name)

#     if not doc.scope_summary or not doc.scope_summary.strip():
#         frappe.throw("Please fill the Scope Summary before asking for rate.")

#     prompt = f"""
# Based on the following tender scope, suggest a bidding rate (in INR ₹ or Rs.) and provide cost justification.

# Scope:
# {doc.scope_summary}
# """

#     try:
#         client = get_groq_client()
#         response = client.chat.completions.create(
#             model="llama3-70b-8192",
#             messages=[{"role": "user", "content": prompt}]
#         )

#         result = response.choices[0].message.content
#         doc.cost_justification = result

#         # ₹ or Rs. extractor
#         rate_match = re.search(r'(₹|Rs\.?)\s?([\d,]+)', result)
#         if rate_match:
#             clean_rate = rate_match.group(2).replace(",", "")
#             doc.suggested_rate = float(clean_rate)

#         doc.save()
#         return "Rate suggestion saved."

#     except OpenAIError as e:
#         frappe.throw(f"Groq rate suggestion failed: {e}")


# @frappe.whitelist()
# def run_manual_prompt(name):
#     doc = frappe.get_doc("Tender", name)

#     if not doc.manual_ai_prompt or not doc.manual_ai_prompt.strip():
#         frappe.throw("Please write something in the Manual AI Prompt field.")

#     try:
#         client = get_groq_client()
#         response = client.chat.completions.create(
#             model="llama3-70b-8192",
#             messages=[{"role": "user", "content": doc.manual_ai_prompt}]
#         )

#         result = response.choices[0].message.content
#         doc.ai_response = result
#         doc.save()
#         return "Manual prompt executed."

#     except OpenAIError as e:
#         frappe.throw(f"Groq manual prompt failed: {e}")
# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
import requests
import tempfile
import re
from frappe.utils import today
from openai import OpenAI, OpenAIError


class Tender(Document):
    def before_save(self):
        if not self.upload_date:
            self.upload_date = today()


def get_groq_client():
    return OpenAI(
        api_key=frappe.conf.get("groq_api_key"),
        base_url="https://api.groq.com/openai/v1"
    )


@frappe.whitelist()
def extract_summary(name):
    import fitz  # ✅ Safe to import here
    import json
    from dateutil import parser

    doc = frappe.get_doc("Tender", name)

    if not doc.tender_pdf:
        frappe.throw("Please attach or link a Tender PDF.")

    # Handle file download (external or internal)
    if doc.tender_pdf.startswith("http://") or doc.tender_pdf.startswith("https://"):
        response = requests.get(doc.tender_pdf)
        if response.status_code != 200:
            frappe.throw("Failed to download the PDF from the provided URL.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        pdf_path = tmp_file_path
    else:
        pdf_path = frappe.get_site_path("public", doc.tender_pdf.replace("/files/", "files/"))

    with fitz.open(pdf_path) as pdf:
        text = "\n".join(page.get_text() for page in pdf)

    # AI Prompt
    prompt = f"""
From the following tender document, extract:

1. Scope of Work
2. Eligibility Criteria
3. Required Documents

Also, return the following dates in this exact JSON format:
{{
  "submission_date": "YYYY-MM-DD",
  "emd_deadline": "YYYY-MM-DD",
  "pre_bid_date": "YYYY-MM-DD"
}}

If a date is not found, use null.

Tender Text:
{text[:6000]}
"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content

        # Text fields
        doc.scope_of_work = result.split("Eligibility")[0].strip()
        if "Eligibility" in result and "Required" in result:
            doc.eligibility_criteria = result.split("Eligibility")[1].split("Required")[0].strip()
            doc.required_documents = result.split("Required")[1].split("{")[0].strip()

        # Parse JSON date block
        json_match = re.search(r'\{[\s\S]+?\}', result)
        if json_match:
            try:
                dates = json.loads(json_match.group(0))
                for field in ["submission_date", "emd_deadline", "pre_bid_date"]:
                    raw = dates.get(field)
                    if raw and raw != "null":
                        parsed = parser.parse(raw).date().isoformat()
                        setattr(doc, field, parsed)
            except Exception as e:
                frappe.log_error(str(e), "Tender Date JSON Parsing Error")

        doc.save()

    except OpenAIError as e:
        frappe.throw(f"Groq API error: {e}")

    finally:
        if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

    return "Summary and dates extracted successfully."


@frappe.whitelist()
def ask_ai_for_rate(name):
    doc = frappe.get_doc("Tender", name)

    if not doc.scope_summary or not doc.scope_summary.strip():
        frappe.throw("Please fill the Scope Summary before asking for rate.")

    prompt = f"""
Based on the following tender scope, suggest a bidding rate (in INR ₹ or Rs.) and provide cost justification.

Scope:
{doc.scope_summary}
"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content
        doc.cost_justification = result

        # ₹ or Rs. extractor
        rate_match = re.search(r'(₹|Rs\.?)\s?([\d,]+)', result)
        if rate_match:
            clean_rate = rate_match.group(2).replace(",", "")
            doc.suggested_rate = float(clean_rate)

        doc.save()
        return "Rate suggestion saved."

    except OpenAIError as e:
        frappe.throw(f"Groq rate suggestion failed: {e}")


@frappe.whitelist()
def run_manual_prompt(name):
    doc = frappe.get_doc("Tender", name)

    if not doc.manual_ai_prompt or not doc.manual_ai_prompt.strip():
        frappe.throw("Please write something in the Manual AI Prompt field.")

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": doc.manual_ai_prompt}]
        )

        result = response.choices[0].message.content
        doc.ai_response = result
        doc.save()
        return "Manual prompt executed."

    except OpenAIError as e:
        frappe.throw(f"Groq manual prompt failed: {e}")
