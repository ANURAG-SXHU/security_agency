import frappe
from frappe.model.document import Document
from frappe.utils import today, cstr

class WorkOrderBilling(Document):
    def before_save(self):
        if not getattr(self, "upload_date", None):
            self.upload_date = today()
        # calculate_charges_breakup(self)
    def validate(self):
        calculate_job_rate_breakup(self)



def calculate_job_rate_breakup(doc, method=None):
    percentage_lookup = {}

    frappe.logger().debug("🔍 Building percentage lookup from Charges Breakup table...")
    print("🔍 Building percentage lookup from Charges Breakup table...")

    for row in doc.rate_breakup:
        percentage_lookup[row.job_description] = {
            "leave_wages": float(row.leave_wages or 0),
            "national_and_festival_holidays": float(row.national_and_festival_holidays or 0),
            "epf": float(row.epf or 0),
            "esic": float(row.esic or 0),
            "reliver_charges": float(row.reliver_charges or 0),
            "service_charges": float(row.service_charges or 0),
            "total_days": int(row.total_days or 26),  # ✅ Fallback to 26 if empty
        }
        log_msg = f"✔️ {row.job_description} => {percentage_lookup[row.job_description]}"
        frappe.logger().debug(log_msg)
        print(log_msg)

    frappe.logger().debug("🚀 Starting calculations for each Job Rate row...")
    print("🚀 Starting calculations for each Job Rate row...")

    for row in doc.job_rate_details:
        desc = row.job_description

        if desc not in percentage_lookup:
            msg = f"⚠️ No rate breakup found for job description: {desc}"
            frappe.msgprint(msg)
            frappe.logger().debug(msg)
            print(msg)
            continue

        perc = percentage_lookup[desc]
        total_days = perc["total_days"]

        # ✅ Auto-calculate minimum_wages_per_month from rate_per_day
        if row.rate_per_day:
            row.minimum_wages_per_month = round(row.rate_per_day * total_days, 2)
            frappe.logger().debug(f"📌 Auto-calculated minimum_wages_per_month for '{desc}': {row.minimum_wages_per_month}")
            print(f"📌 Auto-calculated minimum_wages_per_month for '{desc}': {row.minimum_wages_per_month}")

        mw = float(row.minimum_wages_per_month or 0)

        if mw == 0:
            msg = f"❌ Minimum wage is 0 for job: {desc}. Skipping..."
            frappe.logger().debug(msg)
            print(msg)
            continue

        # 🧮 Apply updated formulas
        leave = round((mw / total_days) * perc["leave_wages"]/12, 2)
        holiday = round((mw / total_days) * perc["national_and_festival_holidays"]/12, 2)
        wage = mw + leave + holiday
        epf = round((perc["epf"] / 100) * wage, 2)
        esic = round((perc["esic"] / 100) * wage, 2)
        gross = wage + epf + esic
        reliever = round(mw * (perc["reliver_charges"] / 100), 2)  # ✅ if you want percentage-based reliever
        service = round((gross * perc["service_charges"]) / 100, 2)
        total = gross + reliever + service

        # 🔄 Shift Multiplier Logic (Updated per_day calculation)
        shift_multiplier = int(row.number_of_shifts or 1)
        per_day = total * shift_multiplier

        # 🔎 Debug Values
        debug_data = {
            "Leave Wages": leave,
            "Holiday Wages": holiday,
            "Wages": wage,
            "EPF": epf,
            "ESIC": esic,
            "Gross Wages": gross,
            "Reliever Charges": reliever,
            "Service Charges": service,
            "Total Monthly Payable": total,
            "Total Per Day (Shifts Applied)": per_day
        }

        for key, val in debug_data.items():
            msg = f"{key}: {val:.2f}"
            frappe.logger().debug(msg)
            print(msg)

        # 📝 Set values in child row
        row.leave_wages = leave
        row.national_and_festival_holidays = holiday
        row.wages = wage
        row.epf = epf
        row.esic = esic
        row.statutory_benefit = round(epf + esic, 2)
        row.gross_wages = round(gross, 2)
        row.reliver_charges = reliever
        row.service_charges = service
        row.total_monthly_payable = round(total, 2)
        row.total_per_day = per_day

    # 🔁 Update total amount in parent doc
    doc.amount = sum([row.total_monthly_payable or 0 for row in doc.job_rate_details])
    final_msg = f"💰 Updated total amount on doc: {doc.amount}"
    frappe.logger().debug(final_msg)
    print(final_msg)


# ---------------------- OpenAI Client ----------------------
def get_openai_client():
    from openai import OpenAI
    return OpenAI(api_key=frappe.conf.get("openai_api_key"))


# ---------------------- AWS S3 & Textract ----------------------
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


# ---------------------- Extract Work Order Info ----------------------
@frappe.whitelist()
def extract_work_order_info(name):
    import os, tempfile, requests, time, re, json

    doc = frappe.get_doc("Work Order Billing", name)

    if not doc.work_order_pdf:
        frappe.throw("❌ Please attach the Work Order PDF.")

    # -------- Download PDF
    if doc.work_order_pdf.startswith("http"):
        response = requests.get(doc.work_order_pdf)
        if response.status_code != 200:
            frappe.throw("❌ Failed to download PDF.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            pdf_path = tmp.name
    else:
        pdf_path = frappe.get_site_path("public", doc.work_order_pdf.replace("/files/", "files/"))

    # -------- Upload to S3 & run Textract
    s3_key = f"work_orders/{name}.pdf"
    upload_to_s3(pdf_path, s3_key)
    job_id = start_textract_job(s3_key)

    while True:
        result = get_textract_result(job_id)
        status = result["JobStatus"]
        if status == "SUCCEEDED":
            break
        elif status == "FAILED":
            frappe.throw("❌ Textract job failed.")
        time.sleep(5)

    # -------- Extract text
    text = "\n".join([b["Text"] for b in result["Blocks"] if b["BlockType"] == "LINE"])
    frappe.msgprint(f"📄 Textract Text Preview:<br><pre>{text[:1000]}</pre>")

    # -------- Regex fallback for single rate
    regex_pattern = r"(?:Rate per man day|Rate per day|Rate/day)[^\d]{0,10}(\d{2,6}(?:\.\d{1,2})?)"
    matches = re.findall(regex_pattern, text, re.IGNORECASE)
    rates = [float(m) for m in matches if 100 <= float(m) <= 2000]

    if rates:
        max_rate = max(rates)
        doc.rate_per_day = max_rate
        doc.save()
        frappe.msgprint(f"✅ Regex fallback rate: ₹{max_rate}")
        return f"✅ Regex fallback rate saved: ₹{max_rate}"

    # -------- Otherwise use OpenAI for multiple job roles
    client = get_openai_client()
    prompt = prompt = f"""
You are a smart work order reader.

Below is OCR text:
{text[:8000]}

Extract ALL job designations and their exact *Rate per man day* as shown in the text.
DO NOT recalculate from monthly or hourly if *Rate per man day* is directly available.

Return JSON array ONLY:
[
  {{"job_description": "...", "rate_per_day": 392.00}},
  ...
]
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content
    frappe.msgprint(f"🧠 OpenAI Response:<br><pre>{result}</pre>")

    json_match = re.search(r"\[\s*\{[\s\S]+?\}\s*\]", result)
    if not json_match:
        frappe.throw("❌ Could not parse JSON array from AI.")

    job_rates = json.loads(json_match.group(0))

    doc.set("job_rate_details", [])
    for item in job_rates:
        desc = item.get("job_description")
        rate = item.get("rate_per_day")
        if desc and rate:
            doc.append("job_rate_details", {
                "job_description": desc.strip(),
                "rate_per_day": float(rate)
            })
    doc.set("rate_breakup", [])
    for item in job_rates:
        desc = item.get("job_description")
        if desc and rate:
            doc.append("rate_breakup", {
                "job_description": desc.strip(),
            })

    valid_rates = [r.get("rate_per_day") for r in job_rates if r.get("rate_per_day")]
    if valid_rates:
        doc.rate_per_day = max(valid_rates)

    doc.save()
    return f"✅ Extracted {len(job_rates)} job rates and saved."

# ---------------------- Attendance XLS Parser ----------------------
@frappe.whitelist()
def parse_attendance_xlsx(name):
    import pandas as pd

    doc = frappe.get_doc("Work Order Billing", name)

    if not doc.attendance_xls:
        frappe.throw("❌ Please attach Attendance XLS file.")

    file_path = frappe.get_site_path("public", doc.attendance_xls.replace("/files/", "files/"))
    df = pd.read_excel(file_path, engine='openpyxl')

    required_columns = {"Employee Name", "Status", "Job Description", "Date"}
    if not required_columns.issubset(df.columns):
        frappe.throw("❌ Required columns missing in XLS.")

    attendance_map = {}
    for _, row in df.iterrows():
        emp = cstr(row.get("Employee Name", "")).strip()
        status = cstr(row.get("Status", "")).strip().lower()
        job = cstr(row.get("Job Description", "")).strip()
        date = row.get("Date")

        if emp and job and date and status == "present":
            key = (emp, job, date)
            attendance_map[key] = attendance_map.get(key, 0) + 1

    rate_lookup = {
        row.job_description.strip(): row.rate_per_day
        for row in doc.job_rate_details or []
    }

    doc.set("guard_attendance_table", [])

    total_days = 0
    total_amount = 0.0

    for (emp, job, att_date), days in attendance_map.items():
        rate = float(rate_lookup.get(job, 0))
        amount = rate * days
        total_days += days
        total_amount += amount

        doc.append("guard_attendance_table", {
            "employee_name": emp,
            "job_description": job,
            "present_days": days,
            "date": att_date
        })

    doc.total_present_days = total_days
    doc.amount = total_amount

    doc.save()
    return f"✅ Parsed rows: {len(attendance_map)}, Total Days: {total_days}, Total Amount: ₹{total_amount:.2f}"


# ---------------------- Attendance Template ----------------------
@frappe.whitelist()
def download_attendance_template(docname=None):
    import pandas as pd
    import os
    from frappe.utils import get_site_path
    from datetime import date

    df = pd.DataFrame([{
        "Employee Name": "Ramesh Kumar",
        "Job Description": "Security Guard",
        "Status": "Present",
        "Date": date.today().strftime("%Y-%m-%d")
    }])

    filename = f"Attendance_Template_{docname or 'template'}.xlsx"
    file_path = os.path.join(get_site_path("public", "files"), filename)
    df.to_excel(file_path, index=False)

    return f"/files/{filename}"

def calculate_charges_breakup(doc):
    # Build a map of percentages from Charges Breakup
    breakup_map = {
        row.job_description.strip(): {
            "leave_wages": row.leave_wages or 0,
            "national_and_festival_holidays": row.national_and_festival_holidays or 0,
            "epf": row.epf or 0,
            "esic": row.esic or 0,
            "reliver_charges": row.reliver_charges or 0,
            "service_charges": row.service_charges or 0,
        }
        for row in doc.rate_breakup or []
    }

    for row in doc.job_rate_details or []:
        desc = row.job_description.strip()
        rate_per_day = float(row.rate_per_day or 0)

        breakup = breakup_map.get(desc, {})

        row.leave_wages = (rate_per_day * breakup.get("leave_wages", 0)) / 100
        row.national_and_festival_holidays = (rate_per_day * breakup.get("national_and_festival_holidays", 0)) / 100
        row.epf = (rate_per_day * breakup.get("epf", 0)) / 100
        row.esic = (rate_per_day * breakup.get("esic", 0)) / 100
        row.reliver_charges = (rate_per_day * breakup.get("reliver_charges", 0)) / 100
        row.service_charges = (rate_per_day * breakup.get("service_charges", 0)) / 100