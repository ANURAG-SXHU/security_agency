# Copyright (c) 2025, Anurag Sahu and contributors
# For license information, please see license.txt

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

    # ✅ Get PDF path (URL or /files/)
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

        # ✅ Improved AI Prompt
        prompt = f"""
You are an expert Government Tender Data Extraction AI.

You must carefully read the tender text below and extract structured data.

STRICT OUTPUT FORMAT:
Your response **must** follow this exact structure and order:

📌 Basic Details:
(Write a short paragraph including Tendering Authority, Tender ID (if found), Work Location, Estimated Project Cost, Project Duration, and any other key details.)

📌 Fee and Security:
- Tender Fee: …
- EMD (Earnest Money Deposit): …
- Performance Security: …
- Bank Guarantee / Security Deposit Rules: …

📌 Scope of Work:
Write 2–3 concise but rich paragraphs describing:
- What work is to be done
- Where and for how long
- Contractor’s key deliverables and constraints
- Any special compliance or environmental/safety rules

📌 Eligibility Criteria:
Bullet list with:
- Required experience (years, project type, size)
- Minimum average annual turnover
- Joint Venture (JV) rules
- Required certifications/licenses
- Solvency proof or financial criteria
- Mandatory EMD payment details

📌 Required Documents:
Bullet list of mandatory documents (technical + financial).

📌 Technical Bid Evaluation:
Explain in 2–4 sentences how technical bids will be scored.
If marks or weightage tables are mentioned, recreate them as Markdown tables.

📌 Tables:
If the tender contains structured tabular data (e.g. BOQ, payment schedule),
convert it into Markdown tables, keeping all columns.

📌 Dates:
Return a valid JSON object at the end (and only at the end) in this format:
{{
  "submission_date": "YYYY-MM-DD",
  "emd_deadline": "YYYY-MM-DD",
  "pre_bid_date": "YYYY-MM-DD"
}}

Rules:
- If EMD Deadline is missing, use the same date as submission_date.
- If Pre-Bid Date is missing, use null.
- Never invent or guess a date.

Tender Text:
{selected_text[:15000]}
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

        # ✅ Fill fields
        doc.basic_details = section_between(result, "📌 Basic Details:", "📌 Fee and Security:")
        doc.fee_and_security = section_between(result, "📌 Fee and Security:", "📌 Scope of Work:")
        doc.scope_of_work = section_between(result, "📌 Scope of Work:", "📌 Eligibility Criteria:")
        doc.eligibility_criteria = section_between(result, "📌 Eligibility Criteria:", "📌 Required Documents:")
        doc.required_documents = section_between(result, "📌 Required Documents:", "📌 Technical Bid Evaluation:")
        doc.text_editor_chcp = section_between(result, "📌 Technical Bid Evaluation:", "📌 Tables:")
        doc.tables_extracted = section_between(result, "📌 Tables:", "{")

        # ✅ Extract JSON dates
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

        # ✅ Short scope summary
        summary_prompt = f"""
You are an assistant summarizer.

Write a single, powerful sentence (max 40 words) describing the core scope of this tender:
- What needs to be built/supplied/executed
- Where
- Any key quantity or duration if found

Avoid extra words, disclaimers, or repetition.

Tender Text:
{selected_text[:5000]}
"""
        frappe.publish_realtime('textract_progress', {'status': 'Getting short scope summary...'})
        summary_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        doc.scope_summary = summary_response.choices[0].message.content.strip()

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

    return "✅ Detailed summary, new fields, short scope summary, and important dates extracted successfully."


@frappe.whitelist()
def ask_ai_for_rate(name):
    import re
    import json
    from openai._exceptions import OpenAIError

    doc = frappe.get_doc("Tender", name)

    base_text = doc.scope_summary or doc.scope_of_work
    if not base_text:
        frappe.throw("Scope Summary or Scope of Work is required to ask for rate.")

    prompt = f"""
You are an Indian public works cost estimator.

Based only on the scope below, estimate a fair market tender value (in INR).
Use current Indian market rates, typical material & labor costs, overheads, and risk margins.

Scope of Work:
{base_text}

Return **only** a strict JSON like:
{{
  "suggested_rate": <numeric_value_in_INR>,
  "cost_justification": "Explain cost drivers (materials, manpower, transport, risk, etc.) in 3–5 full sentences."
}}
"""

    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Always respond with valid JSON only. No prose, no markdown."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.strip()
        frappe.log_error(result, "AI Cost Estimator Raw Output")

        json_match = re.search(r'\{[\s\S]+?\}', result)
        if not json_match:
            frappe.throw(f"❌ Could not find valid JSON in AI output: {result}")

        parsed = json.loads(json_match.group(0))

        doc.suggested_rate = float(parsed.get("suggested_rate", 0))
        doc.cost_justification = parsed.get("cost_justification", "").strip()

        doc.save()
        return "✅ Suggested rate and justification saved."

    except OpenAIError as e:
        frappe.throw(f"OpenAI error: {e}")
    except json.JSONDecodeError as e:
        frappe.throw(f"❌ JSON parse error: {e}")


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
Below is raw text extracted from the tender PDF.

User Query:
{doc.manual_ai_prompt}

Answer precisely and factually.
- If the tender contains tables, recreate them in clean Markdown tables.
- Keep bullet points concise.
- Do not add disclaimers or generic advice.

Tender Text:
{full_text[:15000]}
"""

        frappe.publish_realtime('textract_progress', {'status': 'Sending manual prompt to OpenAI...'})
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": manual_prompt}]
        )

        result = response.choices[0].message.content.strip()

        # ✅ Clean result
        cleaned_result = result
        cleaned_result = re.sub(r'^#+\s*', '', cleaned_result, flags=re.MULTILINE)
        cleaned_result = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_result)
        cleaned_result = re.sub(r'\*(.*?)\*', r'\1', cleaned_result)
        cleaned_result = re.sub(
            r'(please refer.*?\.)|(typically)|(generally)|(for precise details.*?)',
            '',
            cleaned_result,
            flags=re.IGNORECASE
        )
        cleaned_result = re.sub(r'\n\s*\n', '\n\n', cleaned_result).strip()

        doc.ai_response = cleaned_result
        doc.save()
        frappe.publish_realtime('textract_progress', {'status': 'Manual prompt complete & cleaned & saved.'})

        return "Manual prompt executed with PDF context."

    except OpenAIError as e:
        frappe.throw(f"OpenAI manual prompt failed: {e}")

    finally:
        if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
