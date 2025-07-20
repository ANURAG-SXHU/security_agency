# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

# import frappe
# from frappe.model.document import Document
# from frappe.utils import today


# class Tender(Document):
#     def autoname(self):
#         self.name = frappe.model.naming.make_autoname('TEND-.YY.MM.####')

#     def before_save(self):
#         if not self.upload_date:
#             self.upload_date = today()


# def get_openai_client():
#     from openai import OpenAI
#     return OpenAI(
#         api_key=frappe.conf.get("openai_api_key")
#     )


# @frappe.whitelist()
# def extract_summary(name):
#     import re
#     import tempfile
#     import os
#     import json
#     import requests
#     import fitz
#     from dateutil import parser
#     from openai._exceptions import OpenAIError

#     doc = frappe.get_doc("Tender", name)

#     if not doc.tender_pdf:
#         frappe.throw("Please attach or link a Tender PDF.")

#     # Download PDF if URL or use site file
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

#     try:
#         # ✅ Extract with blocks + tabs
#         with fitz.open(pdf_path) as pdf:
#             pages_text = []
#             for page in pdf:
#                 blocks = page.get_text("blocks")
#                 blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
#                 for b in blocks:
#                     block_text = b[4]
#                     cleaned_line = re.sub(r' {2,}', '\t', block_text)
#                     pages_text.append(cleaned_line)
#             full_text = "\n".join(pages_text)

#         # ✅ Pick date-related lines if possible
#         filtered_lines = [
#             line for line in full_text.splitlines()
#             if re.search(r'\b(date|submission|bid|deadline|schedule)\b', line, re.I)
#         ]
#         selected_text = "\n".join(filtered_lines) if filtered_lines else full_text

#         prompt = f"""
# You are a professional tender summarizer AI.

# Below is raw text from a government tender PDF.
# Use this text to write **detailed**, clear, structured sections for the following:

# 📌 Scope of Work:
# - Write 1–2 detailed paragraphs.
# - Include WHAT work is to be done, WHERE, duration, contractor's main responsibility, and any specific conditions.
# - Example: "The work includes comprehensive cleaning, maintenance, and housekeeping services for the District Court guest houses. The contractor must provide trained manpower, cleaning supplies, equipment, and daily upkeep for all blocks for a period of 12 months."

# 📌 Eligibility Criteria:
# - Write a clear bullet list.
# - Include: minimum experience, average annual turnover, allowed Joint Venture (JV) rules, EMD amount and rules, solvency proof, certifications.
# - Example: "- Minimum 3 years experience.\n- Average annual turnover of Rs. 30 lakhs for last 3 years.\n- JV permitted with max 2 firms.\n- Valid EMD as DD/Bank Guarantee.\n- PAN, GST mandatory."

# 📌 Required Documents:
# - Write each required document as a bullet.
# - Example: "- Copy of PAN Card\n- GST Certificate\n- Power of Attorney\n- EMD DD/BG\n- Past work completion certificates\n- Affidavit as per tender annexure"

# 📌 Tables:
# - If you see rows with tabs, rebuild them as **Markdown tables** with clear headings.
# - Example: "| Item | Qty | Unit | Rate | Amount |"

# 📌 Dates:
# Finally, return only this JSON:
# {{
#   "submission_date": "YYYY-MM-DD",
#   "emd_deadline": "YYYY-MM-DD",
#   "pre_bid_date": "YYYY-MM-DD"
# }}

# 👉 If EMD Deadline is missing, use the same as Submission.
# 👉 If Pre-Bid Date is missing, return null.
# 👉 Do NOT guess or invent dates.

# Tender Text:
# {selected_text[:12000]}
# """

#         client = get_openai_client()
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[{"role": "user", "content": prompt}]
#         )

#         result = response.choices[0].message.content

#         def section_between(bigtext, start, end):
#             if start in bigtext and end in bigtext:
#                 return bigtext.split(start)[1].split(end)[0].strip()
#             return ""

#         doc.scope_of_work = section_between(result, "📌 Scope of Work:", "📌 Eligibility Criteria:")
#         doc.eligibility_criteria = section_between(result, "📌 Eligibility Criteria:", "📌 Required Documents:")
#         doc.required_documents = section_between(result, "📌 Required Documents:", "📌 Tables:")
#         doc.tables_extracted = section_between(result, "📌 Tables:", "{")

#         # ✅ Parse JSON with fallback
#         json_match = re.search(r'\{[\s\S]+?\}', result)
#         if json_match:
#             try:
#                 dates = json.loads(json_match.group(0))
#                 frappe.log_error(json.dumps(dates, indent=2), "Tender Dates Raw JSON")

#                 submission_date = dates.get("submission_date")
#                 if submission_date and submission_date != "null":
#                     doc.submission_date = parser.parse(submission_date, dayfirst=True).date().isoformat()

#                 emd_deadline = dates.get("emd_deadline")
#                 if emd_deadline and emd_deadline != "null":
#                     doc.emd_deadline = parser.parse(emd_deadline, dayfirst=True).date().isoformat()
#                 else:
#                     doc.emd_deadline = doc.submission_date

#                 pre_bid_date = dates.get("pre_bid_date")
#                 if pre_bid_date and pre_bid_date != "null":
#                     doc.pre_bid_date = parser.parse(pre_bid_date, dayfirst=True).date().isoformat()
#                 else:
#                     doc.pre_bid_date = None

#             except Exception as e:
#                 frappe.log_error(str(e), "Tender Date JSON Parsing Error")

#         doc.save()

#     except OpenAIError as e:
#         frappe.throw(f"OpenAI API error: {e}")

#     finally:
#         if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
#             os.remove(tmp_file_path)

#     return "Detailed summary, tables, and dates extracted successfully."


# @frappe.whitelist()
# def run_manual_prompt(name):
#     import re
#     import fitz
#     import os
#     import requests
#     import tempfile
#     from openai._exceptions import OpenAIError

#     doc = frappe.get_doc("Tender", name)

#     if not doc.manual_ai_prompt or not doc.manual_ai_prompt.strip():
#         frappe.throw("Please write something in the Manual AI Prompt field.")

#     if not doc.tender_pdf:
#         frappe.throw("Please attach or link a Tender PDF.")

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

#     try:
#         with fitz.open(pdf_path) as pdf:
#             pages_text = []
#             for page in pdf:
#                 blocks = page.get_text("blocks")
#                 blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
#                 for b in blocks:
#                     block_text = b[4]
#                     cleaned_line = re.sub(r' {2,}', '\t', block_text)
#                     pages_text.append(cleaned_line)
#             full_text = "\n".join(pages_text)

#         manual_prompt = f"""
# Below is raw tender PDF text.
# If rows have tabs, treat them as tables and rebuild them as Markdown tables with clear headings.

# User Question:
# {doc.manual_ai_prompt}

# Tender Text:
# {full_text[:12000]}
# """

#         client = get_openai_client()
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[{"role": "user", "content": manual_prompt}]
#         )

#         result = response.choices[0].message.content
#         doc.ai_response = result
#         doc.save()

#         return "Manual prompt executed with PDF context."

#     except OpenAIError as e:
#         frappe.throw(f"OpenAI manual prompt failed: {e}")

#     finally:
#         if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
#             os.remove(tmp_file_path)

import frappe
from frappe.model.document import Document
from frappe.utils import today


class Tender(Document):
    def autoname(self):
        self.name = frappe.model.naming.make_autoname('TEND-.YY.MM.####')

    def before_save(self):
        if not self.upload_date:
            self.upload_date = today()


def get_openai_client():
    from openai import OpenAI
    return OpenAI(
        api_key=frappe.conf.get("openai_api_key")
    )


def upload_to_s3(local_file_path, s3_key):
    import boto3

    s3 = boto3.client(
        "s3",
        aws_access_key_id=frappe.conf.get("aws_access_key_id"),
        aws_secret_access_key=frappe.conf.get("aws_secret_access_key"),
        region_name=frappe.conf.get("aws_region"),
    )

    bucket = frappe.conf.get("s3_bucket")
    s3.upload_file(local_file_path, bucket, s3_key)


def start_textract_job(s3_key):
    import boto3

    textract = boto3.client(
        "textract",
        aws_access_key_id=frappe.conf.get("aws_access_key_id"),
        aws_secret_access_key=frappe.conf.get("aws_secret_access_key"),
        region_name=frappe.conf.get("aws_region"),
    )

    bucket = frappe.conf.get("s3_bucket")

    response = textract.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": s3_key}}
    )

    return response["JobId"]


def get_textract_result(job_id):
    import boto3

    textract = boto3.client(
        "textract",
        aws_access_key_id=frappe.conf.get("aws_access_key_id"),
        aws_secret_access_key=frappe.conf.get("aws_secret_access_key"),
        region_name=frappe.conf.get("aws_region"),
    )

    return textract.get_document_text_detection(JobId=job_id)


@frappe.whitelist()
# def extract_summary(name):
#     import re
#     import tempfile
#     import os
#     import json
#     import requests
#     import time
#     import fitz  # PyMuPDF
#     from dateutil import parser
#     from openai._exceptions import OpenAIError

#     doc = frappe.get_doc("Tender", name)

#     if not doc.tender_pdf:
#         frappe.throw("Please attach or link a Tender PDF.")

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

#     try:
#         full_text = ""

#         # ✅ Try fitz first
#         with fitz.open(pdf_path) as pdf:
#             pages_text = []
#             for page in pdf:
#                 page_text = page.get_text("text")
#                 if page_text.strip():
#                     pages_text.append(page_text)
#             full_text = "\n".join(pages_text)

#         frappe.log_error(full_text[:2000], "FITZ Preview")

#         # ✅ Fallback to Textract if empty
#         if len(full_text.strip()) < 50:
#             frappe.publish_realtime('textract_progress', {'status': 'Fallback: Uploading to Textract...'})
#             s3_key = f"tenders/{name}.pdf"
#             upload_to_s3(pdf_path, s3_key)

#             job_id = start_textract_job(s3_key)

#             while True:
#                 result = get_textract_result(job_id)
#                 status = result["JobStatus"]
#                 frappe.publish_realtime('textract_progress', {'status': f'Textract job status: {status}'})
#                 if status == "SUCCEEDED":
#                     break
#                 elif status == "FAILED":
#                     frappe.throw("Textract job failed.")
#                 time.sleep(5)

#             pages_text = []
#             for block in result["Blocks"]:
#                 if block["BlockType"] == "LINE":
#                     pages_text.append(block["Text"])
#             full_text = "\n".join(pages_text)

#             frappe.log_error(full_text[:2000], "Textract Fallback Preview")

#         selected_text = full_text

#         prompt = f"""
# You are a professional tender summarizer AI.

# Below is raw text from a government tender PDF.

# 👉 Produce the following, **in this exact order**:

# 📌 Scope of Work:
# Write 1–2 detailed paragraphs describing WHAT work is to be done, WHERE, duration, contractor's main responsibility, and any specific conditions.

# 📌 Eligibility Criteria:
# - Write a clear bullet list.
# - Include: minimum experience, average annual turnover, allowed Joint Venture (JV) rules, EMD amount and rules, solvency proof, certifications.
# - Example: "- Minimum 3 years experience.\n- Average annual turnover of Rs. 30 lakhs for last 3 years.\n- JV permitted with max 2 firms.\n- Valid EMD as DD/Bank Guarantee.\n- PAN, GST mandatory."

# 📌 Required Documents:
# - Write each required document as a bullet.
# - Example: "- Copy of PAN Card\n- GST Certificate\n- Power of Attorney\n- EMD DD/BG\n- Past work completion certificates\n- Affidavit as per tender annexure"

# 📌 Tables:
# If you see rows with tabs, rebuild as Markdown tables.

# 📌 Dates:
# Finally, return only this JSON at the end:
# {{
#   "submission_date": "YYYY-MM-DD",
#   "emd_deadline": "YYYY-MM-DD",
#   "pre_bid_date": "YYYY-MM-DD"
# }}

# 👉 If EMD Deadline is missing, use same as Submission.
# 👉 If Pre-Bid Date is missing, return null.
# 👉 Do NOT guess or invent dates.

# Tender Text:
# {selected_text[:12000]}
# """

#         frappe.publish_realtime('textract_progress', {'status': 'Sending text to OpenAI...'})
#         client = get_openai_client()
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[{"role": "user", "content": prompt}]
#         )

#         result = response.choices[0].message.content

#         def section_between(bigtext, start, end):
#             if start in bigtext and end in bigtext:
#                 return bigtext.split(start)[1].split(end)[0].strip()
#             return ""

#         doc.scope_of_work = section_between(result, "📌 Scope of Work:", "📌 Eligibility Criteria:")
#         doc.eligibility_criteria = section_between(result, "📌 Eligibility Criteria:", "📌 Required Documents:")
#         doc.required_documents = section_between(result, "📌 Required Documents:", "📌 Tables:")
#         doc.tables_extracted = section_between(result, "📌 Tables:", "{")

#         json_match = re.search(r'\{[\s\S]+?\}', result)
#         if json_match:
#             try:
#                 dates = json.loads(json_match.group(0))
#                 frappe.log_error(json.dumps(dates, indent=2), "Tender Dates Raw JSON")

#                 submission_date = dates.get("submission_date")
#                 if submission_date and submission_date != "null":
#                     doc.submission_date = parser.parse(submission_date, dayfirst=True).date().isoformat()

#                 emd_deadline = dates.get("emd_deadline")
#                 if emd_deadline and emd_deadline != "null":
#                     doc.emd_deadline = parser.parse(emd_deadline, dayfirst=True).date().isoformat()
#                 else:
#                     doc.emd_deadline = doc.submission_date

#                 pre_bid_date = dates.get("pre_bid_date")
#                 if pre_bid_date and pre_bid_date != "null":
#                     doc.pre_bid_date = parser.parse(pre_bid_date, dayfirst=True).date().isoformat()
#                 else:
#                     doc.pre_bid_date = None

#             except Exception as e:
#                 frappe.log_error(str(e), "Tender Date JSON Parsing Error")

#         doc.save()
#         frappe.publish_realtime('textract_progress', {'status': 'Extraction done & saved.'})

#     except OpenAIError as e:
#         frappe.throw(f"OpenAI API error: {e}")

#     finally:
#         if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
#             os.remove(tmp_file_path)

#     return "Detailed summary, tables, and dates extracted successfully."
@frappe.whitelist()
def extract_summary(name):
    import re
    import tempfile
    import os
    import json
    import requests
    import time
    import fitz  # PyMuPDF
    from dateutil import parser
    from openai._exceptions import OpenAIError

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
        full_text = ""

        # ✅ Try fitz first
        with fitz.open(pdf_path) as pdf:
            pages_text = []
            for page in pdf:
                page_text = page.get_text("text")
                if page_text.strip():
                    pages_text.append(page_text)
            full_text = "\n".join(pages_text)

        frappe.log_error(full_text[:2000], "FITZ Preview")

        # ✅ Fallback to Textract if empty
        if len(full_text.strip()) < 50:
            frappe.publish_realtime('textract_progress', {'status': 'Fallback: Uploading to Textract...'})
            s3_key = f"tenders/{name}.pdf"
            upload_to_s3(pdf_path, s3_key)

            job_id = start_textract_job(s3_key)

            while True:
                result = get_textract_result(job_id)
                status = result["JobStatus"]
                frappe.publish_realtime('textract_progress', {'status': f'Textract job status: {status}'})
                if status == "SUCCEEDED":
                    break
                elif status == "FAILED":
                    frappe.throw("Textract job failed.")
                time.sleep(5)

            pages_text = []
            for block in result["Blocks"]:
                if block["BlockType"] == "LINE":
                    pages_text.append(block["Text"])
            full_text = "\n".join(pages_text)

            frappe.log_error(full_text[:2000], "Textract Fallback Preview")

        selected_text = full_text

        prompt = f"""
You are a professional tender summarizer AI.

Below is raw text from a government tender PDF.

👉 Produce the following, **in this exact order**:

📌 Scope of Work:
Write 1–2 detailed paragraphs describing WHAT work is to be done, WHERE, duration, contractor's main responsibility, and any specific conditions.

📌 Eligibility Criteria:
- Write a clear bullet list.
- Include: minimum experience, average annual turnover, allowed Joint Venture (JV) rules, EMD amount and rules, solvency proof, certifications.
- Example: "- Minimum 3 years experience.\n- Average annual turnover of Rs. 30 lakhs for last 3 years.\n- JV permitted with max 2 firms.\n- Valid EMD as DD/Bank Guarantee.\n- PAN, GST mandatory."

📌 Required Documents:
- Write each required document as a bullet.
- Example: "- Copy of PAN Card\n- GST Certificate\n- Power of Attorney\n- EMD DD/BG\n- Past work completion certificates\n- Affidavit as per tender annexure"

📌 Tables:
If you see rows with tabs, rebuild as Markdown tables.

📌 Dates:
Finally, return only this JSON at the end:
{{
  "submission_date": "YYYY-MM-DD",
  "emd_deadline": "YYYY-MM-DD",
  "pre_bid_date": "YYYY-MM-DD"
}}

👉 If EMD Deadline is missing, use same as Submission.
👉 If Pre-Bid Date is missing, return null.
👉 Do NOT guess or invent dates.

Tender Text:
{selected_text[:12000]}
"""

        frappe.publish_realtime('textract_progress', {'status': 'Sending text to OpenAI...'})
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content

        def section_between(bigtext, start, end):
            if start in bigtext and end in bigtext:
                return bigtext.split(start)[1].split(end)[0].strip()
            return ""

        doc.scope_of_work = section_between(result, "📌 Scope of Work:", "📌 Eligibility Criteria:")
        doc.eligibility_criteria = section_between(result, "📌 Eligibility Criteria:", "📌 Required Documents:")
        doc.required_documents = section_between(result, "📌 Required Documents:", "📌 Tables:")
        doc.tables_extracted = section_between(result, "📌 Tables:", "{")

        json_match = re.search(r'\{[\s\S]+?\}', result)
        if json_match:
            try:
                dates = json.loads(json_match.group(0))
                frappe.log_error(json.dumps(dates, indent=2), "Tender Dates Raw JSON")

                submission_date = dates.get("submission_date")
                if submission_date and submission_date != "null":
                    doc.submission_date = parser.parse(submission_date, dayfirst=True).date().isoformat()

                emd_deadline = dates.get("emd_deadline")
                if emd_deadline and emd_deadline != "null":
                    doc.emd_deadline = parser.parse(emd_deadline, dayfirst=True).date().isoformat()
                else:
                    doc.emd_deadline = doc.submission_date

                pre_bid_date = dates.get("pre_bid_date")
                if pre_bid_date and pre_bid_date != "null":
                    doc.pre_bid_date = parser.parse(pre_bid_date, dayfirst=True).date().isoformat()
                else:
                    doc.pre_bid_date = None

            except Exception as e:
                frappe.log_error(str(e), "Tender Date JSON Parsing Error")

        # ✅ NEW: Get short scope summary
        summary_prompt = f"""
Below is the same tender text.
👉 Write a crisp 1–2 line summary of the scope for a busy manager.

Tender Text:
{selected_text[:5000]}
"""
        frappe.publish_realtime('textract_progress', {'status': 'Getting short scope summary...'})
        summary_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        doc.scope_summary = summary_response.choices[0].message.content.strip()

        # ✅ NEW: Format important dates nicely
        important_dates_str = f"""
- Submission Date: {doc.submission_date or 'N/A'}
- EMD Deadline: {doc.emd_deadline or 'N/A'}
- Pre-Bid Date: {doc.pre_bid_date or 'N/A'}
""".strip()
        doc.important_dates = important_dates_str

        doc.save()
        frappe.publish_realtime('textract_progress', {'status': 'Extraction done & saved.'})

    except OpenAIError as e:
        frappe.throw(f"OpenAI API error: {e}")

    finally:
        if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

    return "Detailed summary, tables, short scope summary, and important dates extracted successfully."
@frappe.whitelist()
def ask_ai_for_rate(name):
    import re
    from openai._exceptions import OpenAIError

    doc = frappe.get_doc("Tender", name)

    # Use scope summary first, fallback to scope of work
    base_text = doc.scope_summary or doc.scope_of_work
    if not base_text:
        frappe.throw("Scope Summary or Scope of Work is required to ask for rate.")

    prompt = f"""
You are a cost estimator AI.

Below is the scope of work:

{base_text}

👉 Suggest a fair market rate for this tender in INR, considering standard rates in India.
👉 Give a clear cost justification.
👉 Return only this JSON at the end:
{{
  "suggested_rate": "number",
  "cost_justification": "your explanation"
}}
"""

    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content

        json_match = re.search(r'\{[\s\S]+?\}', result)
        if json_match:
            import json
            parsed = json.loads(json_match.group(0))
            doc.suggested_rate = float(parsed.get("suggested_rate", 0))
            doc.cost_justification = parsed.get("cost_justification", "").strip()
            doc.save()
            return "Suggested rate and justification saved."
        else:
            frappe.throw("Could not parse AI response.")

    except OpenAIError as e:
        frappe.throw(f"OpenAI error: {e}")


@frappe.whitelist()
def run_manual_prompt(name):
    import re
    import os
    import requests
    import tempfile
    import time
    import fitz  # PyMuPDF
    from openai._exceptions import OpenAIError

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
        full_text = ""

        # Try fitz first
        with fitz.open(pdf_path) as pdf:
            pages_text = []
            for page in pdf:
                page_text = page.get_text("text")
                if page_text.strip():
                    pages_text.append(page_text)
            full_text = "\n".join(pages_text)

        frappe.log_error(full_text[:2000], "FITZ Preview Manual Prompt")

        if len(full_text.strip()) < 50:
            frappe.publish_realtime('textract_progress', {'status': 'Fallback: Uploading to Textract...'})
            s3_key = f"tenders/{name}.pdf"
            upload_to_s3(pdf_path, s3_key)

            job_id = start_textract_job(s3_key)

            while True:
                result = get_textract_result(job_id)
                status = result["JobStatus"]
                frappe.publish_realtime('textract_progress', {'status': f'Textract job status: {status}'})
                if status == "SUCCEEDED":
                    break
                elif status == "FAILED":
                    frappe.throw("Textract job failed.")
                time.sleep(5)

            pages_text = []
            for block in result["Blocks"]:
                if block["BlockType"] == "LINE":
                    pages_text.append(block["Text"])
            full_text = "\n".join(pages_text)

            frappe.log_error(full_text[:2000], "Textract Fallback Manual Prompt")

        manual_prompt = f"""
Below is raw tender PDF text.
Treat rows with tabs as Markdown tables if any.

User Question:
{doc.manual_ai_prompt}

Tender Text:
{full_text[:12000]}
"""

        frappe.publish_realtime('textract_progress', {'status': 'Sending manual prompt to OpenAI...'})
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": manual_prompt}]
        )

        result = response.choices[0].message.content
        doc.ai_response = result
        doc.save()
        frappe.publish_realtime('textract_progress', {'status': 'Manual prompt complete & saved.'})

        return "Manual prompt executed with PDF context."

    except OpenAIError as e:
        frappe.throw(f"OpenAI manual prompt failed: {e}")

    finally:
        if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)



