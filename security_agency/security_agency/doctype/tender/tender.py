# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today


class Tender(Document):
    def before_save(self):
        if not self.upload_date:
            self.upload_date = today()


def get_groq_client():
    from openai import OpenAI
    return OpenAI(
        api_key=frappe.conf.get("groq_api_key"),
        base_url="https://api.groq.com/openai/v1"
    )


@frappe.whitelist()
def extract_summary(name):
    import re
    import tempfile
    import os
    import json
    import requests
    import fitz
    from dateutil import parser
    from openai import OpenAIError

    doc = frappe.get_doc("Tender", name)

    if not doc.tender_pdf:
        frappe.throw("Please attach or link a Tender PDF.")

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

    try:
        with fitz.open(pdf_path) as pdf:
            text = "\n".join(page.get_text() for page in pdf)

        prompt = f"""
From the following tender document, extract and return the following in this format:

📌 Scope of Work:
<paragraph about the scope and timeline>

📌 Eligibility Criteria:
- Bullet points listing eligibility rules, including JV conditions, turnover, etc.

📌 Required Documents:
- Bullet points listing required documents like PAN, GST, POA, JV Agreement, etc.

At the end, return these dates in JSON format:
{{
  "submission_date": "YYYY-MM-DD",
  "emd_deadline": "YYYY-MM-DD",
  "pre_bid_date": "YYYY-MM-DD"
}}

If a date is not found, return null.

Tender Text:
{text[:6000]}
"""

        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content

        # Clean & extract structured sections
        def section_between(text, start, end):
            if start in text and end in text:
                return text.split(start)[1].split(end)[0].strip()
            return ""

        doc.scope_of_work = section_between(result, "📌 Scope of Work:", "📌 Eligibility Criteria:")
        doc.eligibility_criteria = section_between(result, "📌 Eligibility Criteria:", "📌 Required Documents:")
        doc.required_documents = section_between(result, "📌 Required Documents:", "{")

        # Extract JSON date block
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
    import re
    from openai import OpenAIError

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
    import fitz
    import os
    import requests
    import tempfile
    from openai import OpenAIError

    doc = frappe.get_doc("Tender", name)

    if not doc.manual_ai_prompt or not doc.manual_ai_prompt.strip():
        frappe.throw("Please write something in the Manual AI Prompt field.")

    if not doc.tender_pdf:
        frappe.throw("Please attach or link a Tender PDF.")

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

    try:
        with fitz.open(pdf_path) as pdf:
            text = "\n".join(page.get_text() for page in pdf)

        full_prompt = f"""
The following is a tender document. Use it to answer the user's prompt.

--- Tender Document Content (Partial) ---
{text[:6000]}

--- User Prompt ---
{doc.manual_ai_prompt}
"""

        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": full_prompt}]
        )

        result = response.choices[0].message.content
        doc.ai_response = result
        doc.save()
        return "Manual prompt executed with PDF context."

    except OpenAIError as e:
        frappe.throw(f"Groq manual prompt failed: {e}")

    finally:
        if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
