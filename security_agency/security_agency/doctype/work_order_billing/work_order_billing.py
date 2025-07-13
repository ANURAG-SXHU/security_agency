# import frappe
# from frappe.model.document import Document
# from frappe.utils import today, cstr

# class WorkOrderBilling(Document):
#     def before_save(self):
#         if not self.upload_date:
#             self.upload_date = today()
#         # if self.rate_per_day and self.total_present_days:
#         #     self.amount = float(self.rate_per_day) * int(self.total_present_days)

# # ------------------ Groq Client ------------------

# def get_groq_client():
#     from openai import OpenAI
#     return OpenAI(
#         api_key=frappe.conf.get("groq_api_key"),
#         base_url="https://api.groq.com/openai/v1"
#     )

# # ------------------ Fast OCR (Page 1, DPI 100) ------------------

# def extract_text_with_ocr(pdf_path):
#     import fitz
#     from PIL import Image
#     import pytesseract
#     import time

#     with fitz.open(pdf_path) as doc:
#         first_page_text = doc[0].get_text().strip()
#         if first_page_text:
#             return first_page_text

#         frappe.msgprint("📃 No extractable text. Running fast OCR on Page 1...")
#         start = time.time()
#         pix = doc[0].get_pixmap(dpi=100)
#         img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#         text = pytesseract.image_to_string(img)
#         elapsed = round(time.time() - start, 2)
#         frappe.msgprint(f"🧠 OCR Page 1 took {elapsed} sec")
#         return text

# # ------------------ Extract Work Order Info ------------------

# @frappe.whitelist()
# def extract_work_order_info(name):
#     import os
#     import tempfile
#     import re
#     import json
#     import requests
#     import fitz
#     import time
#     from openai import OpenAIError

#     frappe.msgprint(f"⚙️ Extracting info for: {name}")
#     doc = frappe.get_doc("Work Order Billing", name)

#     if not doc.work_order_pdf:
#         frappe.throw("Please attach the Work Order PDF.")

#     try:
#         # Step 1: Load PDF
#         if doc.work_order_pdf.startswith("http"):
#             response = requests.get(doc.work_order_pdf)
#             if response.status_code != 200:
#                 frappe.throw("❌ Failed to download PDF.")
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#                 tmp.write(response.content)
#                 pdf_path = tmp.name
#         else:
#             pdf_path = frappe.get_site_path("public", doc.work_order_pdf.replace("/files/", "files/"))

#         # Step 2: Extract text
#         text = extract_text_with_ocr(pdf_path)
#         if not text.strip():
#             frappe.throw("❌ OCR failed. No readable text found.")

#         frappe.msgprint(f"📄 Text Preview:<br><pre>{text[:1500]}</pre>")

#         # Step 3: Try regex (fallback legacy)
#         pattern = r"(?:Rate per man day|Rate per day|Rate\/day)[^\d]{0,10}(\d{2,5}(?:\.\d{1,2})?)"
#         matches = re.findall(pattern, text, re.IGNORECASE)
#         rates = [float(m) for m in matches if 100 <= float(m) <= 1000]
#         if rates:
#             max_rate = max(rates)
#             doc.rate_per_day = max_rate
#             doc.save()
#             frappe.msgprint(f"✅ Regex fallback rate: ₹{max_rate}")
#             return "✅ Rate extracted using regex."

#         # Step 4: Groq AI (multi-role rates)
#         prompt = f"""
# You're a quotation reader. Extract all job designations and their per-day rate.

# Return JSON array:
# [
#   {{ "job_description": "Security Guard", "rate_per_day": 625 }},
#   {{ "job_description": "Supervisor", "rate_per_day": 750 }}
# ]

# If rate is monthly/hourly, convert to per-day (26 working days/month, 8 hrs/day).

# --- Start ---
# {text[:8000]}
# --- End ---
# """
#         client = get_groq_client()
#         start = time.time()
#         response = client.chat.completions.create(
#             model="llama3-70b-8192",
#             messages=[{"role": "user", "content": prompt}]
#         )
#         elapsed = round(time.time() - start, 2)
#         result = response.choices[0].message.content or ""
#         frappe.msgprint(f"🧠 Groq AI Output ({elapsed}s):<br><pre>{result}</pre>")

#         json_match = re.search(r"\[\s*\{[\s\S]+?\}\s*\]", result)
#         if json_match:
#             job_rates = json.loads(json_match.group(0))
#             doc.set("job_rate_details", [])
#             for item in job_rates:
#                 desc = item.get("job_description")
#                 rate = item.get("rate_per_day")
#                 if desc and rate:
#                     doc.append("job_rate_details", {
#                         "job_description": desc,
#                         "rate_per_day": float(rate)
#                     })

#             # Optional: set max rate as fallback
#             valid_rates = [r.get("rate_per_day") for r in job_rates if r.get("rate_per_day")]
#             if valid_rates:
#                 doc.rate_per_day = max(valid_rates)

#             doc.save()
#             return f"✅ Extracted {len(job_rates)} job rates from Groq AI."

#         frappe.throw("❌ Groq could not return valid job rate list.")

#     except OpenAIError as e:
#         frappe.log_error(str(e), "Groq OpenAIError")
#         frappe.throw("⚠️ Groq API error.")
#     finally:
#         if "pdf_path" in locals() and os.path.exists(pdf_path):
#             os.remove(pdf_path)

# # ------------------ Attendance XLS Parser ------------------


# @frappe.whitelist()
# # def parse_attendance_xlsx(name):
# #     import pandas as pd
# #     from frappe.utils import cstr

# #     frappe.msgprint(f"⚙️ Parsing attendance for: {name}")
# #     doc = frappe.get_doc("Work Order Billing", name)

# #     if not doc.attendance_xls:
# #         frappe.throw("Please upload Attendance XLS file.")

# #     try:
# #         file_path = frappe.get_site_path("public", doc.attendance_xls.replace("/files/", "files/"))
# #         df = pd.read_excel(file_path)

# #         required_columns = {"Employee Name", "Status", "Job Description", "Date"}
# #         if not required_columns.issubset(df.columns):
# #             frappe.throw("❌ Required columns missing. Make sure Excel has: 'Employee Name', 'Status', 'Job Description', and 'Date'.")

# #         # Step 1: Group by (employee, job, date)
# #         attendance_map = {}  # { (employee_name, job_description, date): count }
# #         for _, row in df.iterrows():
# #             emp = cstr(row.get("Employee Name", "")).strip()
# #             status = cstr(row.get("Status", "")).strip().lower()
# #             job = cstr(row.get("Job Description", "")).strip()
# #             date = row.get("Date")

# #             if emp and job and date and status == "present":
# #                 key = (emp, job, date)
# #                 attendance_map[key] = attendance_map.get(key, 0) + 1

# #         # Step 2: Build job rate lookup
# #         rate_lookup = {
# #             row.job_description.strip(): row.rate_per_day
# #             for row in doc.job_rate_details or []
# #         }

# #         # Step 3: Clear existing table
# #         doc.set("guard_attendance_table", [])

# #         total_days = 0
# #         total_amount = 0.0

# #         # Step 4: Append attendance entries
# #         for (emp, job, att_date), days in attendance_map.items():
# #             rate = rate_lookup.get(job)
# #             if rate is None:
# #                 frappe.msgprint(f"⚠️ No rate found for job: {job}. Using ₹0.")
# #                 rate = 0.0

# #             amount = float(rate) * days
# #             total_days += days
# #             total_amount += amount

# #             # Log for verification
# #             frappe.msgprint(f"🧾 {emp} | {job} | {att_date} | {days} × ₹{rate} = ₹{amount}")

# #             doc.append("guard_attendance_table", {
# #                 "employee_name": emp,
# #                 "job_description": job,
# #                 "present_days": days,
# #                 "date": att_date  # ✅ new date field
# #             })

# #         doc.total_present_days = total_days
# #         doc.amount = total_amount

# #         frappe.msgprint(f"✅ Total Present Days: {total_days}<br>💰 Total Amount: ₹{total_amount:.2f}")
# #         doc.save()

# #         return f"✅ Parsed {len(attendance_map)} entries. Total Days: {total_days}, Total Amount: ₹{total_amount:.2f}"

# #     except Exception as e:
# #         frappe.log_error(str(e), "Attendance XLS Parse Error")
# #         frappe.throw("⚠️ Error parsing attendance XLS.")
# @frappe.whitelist()
# def parse_attendance_xlsx(name):
#     import pandas as pd
#     from frappe.utils import cstr, today

#     frappe.msgprint(f"⚙️ Parsing attendance for: {name}")
#     doc = frappe.get_doc("Work Order Billing", name)

#     if not doc.attendance_xls:
#         frappe.throw("Please upload Attendance XLS file.")

#     try:
#         file_path = frappe.get_site_path("public", doc.attendance_xls.replace("/files/", "files/"))
#         frappe.msgprint(f"📁 Resolved file path: {file_path}")

#         df = pd.read_excel(file_path, engine='openpyxl')
#         frappe.msgprint(f"📊 Loaded columns: {list(df.columns)}")

#         required_columns = {"Employee Name", "Status", "Job Description", "Date"}
#         if not required_columns.issubset(df.columns):
#             frappe.throw("❌ Required columns missing. Make sure Excel has: 'Employee Name', 'Status', 'Job Description', and 'Date'.")

#         # Step 1: Group by (employee, job, date)
#         attendance_map = {}  # { (employee_name, job_description, date): count }
#         for _, row in df.iterrows():
#             emp = cstr(row.get("Employee Name", "")).strip()
#             status = cstr(row.get("Status", "")).strip().lower()
#             job = cstr(row.get("Job Description", "")).strip()
#             date = row.get("Date")

#             if emp and job and date and status == "present":
#                 key = (emp, job, date)
#                 attendance_map[key] = attendance_map.get(key, 0) + 1

#         # Step 2: Build job rate lookup
#         rate_lookup = {
#             row.job_description.strip(): row.rate_per_day
#             for row in doc.job_rate_details or []
#         }

#         # Step 3: Clear existing table
#         doc.set("guard_attendance_table", [])

#         total_days = 0
#         total_amount = 0.0

#         # Step 4: Append attendance entries
#         for (emp, job, att_date), days in attendance_map.items():
#             raw_rate = rate_lookup.get(job)
#             try:
#                 rate = float(raw_rate)
#                 if pd.isna(rate):
#                     raise ValueError("Rate is NaN")
#             except:
#                 frappe.msgprint(f"⚠️ No valid rate found for job '{job}'. Using ₹0.")
#                 rate = 0.0

#             amount = rate * days
#             total_days += days
#             total_amount += amount

#             # Log for verification
#             frappe.msgprint(f"🧾 {emp} | {job} | {att_date} | {days} × ₹{rate} = ₹{amount}")

#             doc.append("guard_attendance_table", {
#                 "employee_name": emp or "",
#                 "job_description": job or "",
#                 "present_days": int(days),
#                 "date": att_date or today()
#             })

#         doc.total_present_days = total_days
#         doc.amount = total_amount

#         frappe.msgprint(f"✅ Total Present Days: {total_days}<br>💰 Total Amount: ₹{total_amount:.2f}")
#         doc.save()

#         return f"✅ Parsed {len(attendance_map)} entries. Total Days: {total_days}, Total Amount: ₹{total_amount:.2f}"

#     except Exception as e:
#         frappe.log_error(str(e), "Attendance XLS Parse Error")
#         frappe.throw("⚠️ Error parsing attendance XLS.")

# @frappe.whitelist()
# def download_attendance_template(docname=None):
#     import pandas as pd
#     import os
#     from frappe.utils import get_site_path
#     from datetime import date
#     from frappe import _

#     # Sample DataFrame
#     df = pd.DataFrame([{
#         "Employee Name": "Ramesh Kumar",
#         "Job Description": "Security Guard",
#         "Status": "Present",
#         "Date": date.today().strftime("%Y-%m-%d")
#     }])

#     # File path
#     filename = f"Attendance_Template_{docname or 'template'}.xlsx"
#     file_path = os.path.join(get_site_path("public", "files"), filename)

#     # Save to file
#     df.to_excel(file_path, index=False)

#     frappe.msgprint(_("✅ Template generated successfully."))
#     return f"/files/{filename}"

import frappe
from frappe.model.document import Document
from frappe.utils import today, cstr

class WorkOrderBilling(Document):
    def before_save(self):
        if not self.upload_date:
            self.upload_date = today()

# ------------------ Groq Client ------------------

def get_groq_client():
    from openai import OpenAI
    return OpenAI(
        api_key=frappe.conf.get("groq_api_key"),
        base_url="https://api.groq.com/openai/v1"
    )

# ------------------ PDF Compression ------------------

def compress_pdf(input_path, output_path, scale_factor=0.5):
    import fitz
    pdf = fitz.open(input_path)
    new_pdf = fitz.open()
    for page in pdf:
        pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor))
        img_pdf = fitz.open()
        rect = fitz.Rect(0, 0, pix.width, pix.height)
        img_page = img_pdf.new_page(width=pix.width, height=pix.height)
        img_page.insert_image(rect, pixmap=pix)
        new_pdf.insert_pdf(img_pdf)
        img_pdf.close()
    new_pdf.save(output_path)
    new_pdf.close()
    pdf.close()

# ------------------ OCR.Space Fallback ------------------

def ocr_with_ocrspace(pdf_path):
    import requests, os
    api_key = frappe.conf.get("ocrspace_api_key")
    if not api_key:
        frappe.throw("⚠️ Please configure 'ocrspace_api_key' in site config.")
    if os.path.getsize(pdf_path) > 1024 * 1024:
        frappe.throw("❌ PDF is too large for OCR.Space free plan (max 1 MB). Please compress it or upload a smaller file.")
    with open(pdf_path, "rb") as f:
        resp = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": f},
            data={"apikey": api_key, "OCREngine": "2"}
        )
    data = resp.json()
    if data.get("IsErroredOnProcessing"):
        error = data.get("ErrorMessage") or data.get("ParsedResults", [{}])[0].get("ErrorMessage")
        frappe.throw(f"❌ OCR.Space Error: {error}")
    parsed = data.get("ParsedResults", [])
    return "\n".join(p.get("ParsedText", "") for p in parsed)

# ------------------ Extract Work Order Info ------------------

@frappe.whitelist()
def extract_work_order_info(name):
    import os
    import tempfile
    import re
    import json
    import requests
    import fitz
    import time
    from openai import OpenAIError

    frappe.msgprint(f"⚙️ Extracting info for: {name}")
    doc = frappe.get_doc("Work Order Billing", name)

    if not doc.work_order_pdf:
        frappe.throw("Please attach the Work Order PDF.")

    try:
        # Step 1: Load PDF
        if doc.work_order_pdf.startswith("http"):
            response = requests.get(doc.work_order_pdf)
            if response.status_code != 200:
                frappe.throw("❌ Failed to download PDF.")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(response.content)
                pdf_path = tmp.name
        else:
            pdf_path = frappe.get_site_path("public", doc.work_order_pdf.replace("/files/", "files/"))

        # Step 2: Try direct text extraction
        with fitz.open(pdf_path) as pdf:
            text = "\n".join(page.get_text().strip() for page in pdf if page.get_text().strip())

        # Step 3: If no text found, try OCR fallback
        if not text.strip():
            frappe.msgprint("🔍 No direct text found. Trying compression + OCR fallback...")

            compressed_path = pdf_path.replace(".pdf", "_compressed.pdf")
            compress_pdf(pdf_path, compressed_path)

            if os.path.getsize(compressed_path) > 1024 * 1024:
                frappe.throw("❌ PDF is still too large after compression. Please upload a smaller file.")

            text = ocr_with_ocrspace(compressed_path)

        if not text.strip():
            frappe.throw("❌ Could not extract any text from the PDF (direct or OCR).")

        frappe.msgprint(f"📄 Text Preview:<br><pre>{text[:1500]}</pre>")

        # Step 4: Try regex fallback
        pattern = r"(?:Rate per man day|Rate per day|Rate\/day)[^\d]{0,10}(\d{2,5}(?:\.\d{1,2})?)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        rates = [float(m) for m in matches if 100 <= float(m) <= 1000]
        if rates:
            max_rate = max(rates)
            doc.rate_per_day = max_rate
            doc.save()
            frappe.msgprint(f"✅ Regex fallback rate: ₹{max_rate}")
            return "✅ Rate extracted using regex."

        # Step 5: Groq AI fallback
        prompt = f"""
You're a quotation reader. Extract all job designations and their per-day rate.

Return JSON array:
[
  {{ "job_description": "Security Guard", "rate_per_day": 625 }},
  {{ "job_description": "Supervisor", "rate_per_day": 750 }}
]

If rate is monthly/hourly, convert to per-day (26 working days/month, 8 hrs/day).

--- Start ---
{text[:8000]}
--- End ---
"""
        client = get_groq_client()
        start = time.time()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        elapsed = round(time.time() - start, 2)
        result = response.choices[0].message.content or ""
        frappe.msgprint(f"🧠 Groq AI Output ({elapsed}s):<br><pre>{result}</pre>")

        json_match = re.search(r"\[\s*\{[\s\S]+?\}\s*\]", result)
        if json_match:
            job_rates = json.loads(json_match.group(0))
            doc.set("job_rate_details", [])
            for item in job_rates:
                desc = item.get("job_description")
                rate = item.get("rate_per_day")
                if desc and rate:
                    doc.append("job_rate_details", {
                        "job_description": desc,
                        "rate_per_day": float(rate)
                    })

            valid_rates = [r.get("rate_per_day") for r in job_rates if r.get("rate_per_day")]
            if valid_rates:
                doc.rate_per_day = max(valid_rates)

            doc.save()
            return f"✅ Extracted {len(job_rates)} job rates from Groq AI."

        frappe.throw("❌ Groq could not return valid job rate list.")

    except OpenAIError as e:
        frappe.log_error(str(e), "Groq OpenAIError")
        frappe.throw("⚠️ Groq API error.")
    finally:
        if "pdf_path" in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)
