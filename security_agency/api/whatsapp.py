# import frappe
# import requests
# from frappe.utils.pdf import get_pdf
# from frappe.utils.file_manager import save_file
# from datetime import datetime

# def send_salary_slip_pdf_on_whatsapp(doc, method=None):
#     try:
#         print(f"[WhatsApp] 📌 Hook triggered for Salary Slip: {doc.name}")

#         # Get Employee details
#         employee = frappe.get_doc("Employee", doc.employee)
#         print(f"[WhatsApp] ✅ Found employee: {employee.name}")

#         # Validate WhatsApp number
#         if not employee.custom_whatsapp_number:
#             print(f"[WhatsApp] ❌ No WhatsApp number for {employee.name}")
#             return

#         print(f"[WhatsApp] 📱 Sending to: {employee.custom_whatsapp_number}")

#         # Get the HTML content of the Salary Slip using a custom Print Format
#         html = frappe.get_print(doc.doctype, doc.name, print_format="MTSS SALARY SLIP")
        
#         # Generate PDF from HTML
#         pdf_data = get_pdf(html)

#         # Save PDF file
#         filename = f"{doc.name}.pdf"
#         print(f"[WhatsApp] 🧾 PDF generated: {filename}")

#         _file = save_file(
#             fname=filename,
#             content=pdf_data,
#             dt=doc.doctype,
#             dn=doc.name,
#             is_private=0
#         )
#         file_url = frappe.utils.get_url(_file.file_url)
#         print(f"[WhatsApp] 📂 File saved at: {file_url}")

#         # Extract Month and Year from start_date
#         start_month = datetime.strptime(str(doc.start_date), "%Y-%m-%d").strftime("%B")
#         year = datetime.strptime(str(doc.start_date), "%Y-%m-%d").strftime("%Y")

#         # WhatsApp API settings
#         instance_id = "instance132549"
#         token = "2ixk8g8b41f9jp1v"
#         url = f"https://api.ultramsg.com/{instance_id}/messages/document"

#         # Prepare Payload
#         payload = {
#             "token": token,
#             "to": employee.custom_whatsapp_number,
#             "filename": filename,
#             "document": file_url,
#             "caption": f"Hello {employee.employee_name}, your Salary Slip for {start_month}-{year} is attached."
#         }

#         print(f"[WhatsApp] 📤 Sending payload to UltraMsg...")
#         res = requests.post(url, data=payload)
#         print(f"[WhatsApp] ✅ UltraMsg response: {res.status_code} - {res.text}")

#     except Exception:
#         print(f"[WhatsApp] ❌ Exception occurred:\n{frappe.get_traceback()}")
import frappe
import requests
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from frappe.utils import get_url
from datetime import datetime

def send_salary_slip_pdf_on_whatsapp(doc, method=None):
    """
    Hook function to send a generated Salary Slip PDF to employee via WhatsApp using UltraMsg API.
    """
    try:
        print(f"[WhatsApp] 📌 Hook triggered for Salary Slip: {doc.name}")

        # Get employee document
        employee = frappe.get_doc("Employee", doc.employee)
        print(f"[WhatsApp] ✅ Found employee: {employee.name}")

        # Validate WhatsApp number
        whatsapp_number = employee.get("custom_whatsapp_number")
        if not whatsapp_number:
            print(f"[WhatsApp] ❌ No WhatsApp number found for {employee.name}")
            return

        print(f"[WhatsApp] 📱 Sending to: {whatsapp_number}")

        # Generate HTML from custom Print Format
        html = frappe.get_print(doc.doctype, doc.name, print_format="Test")
        
        # Convert HTML to PDF
        pdf_data = get_pdf(html)
        sanitized_filename = doc.name.replace("/", "-") + ".pdf"
        print(f"[WhatsApp] 🧾 PDF generated: {sanitized_filename}")

        # Save the file in public path
        _file = save_file(
            fname=sanitized_filename,
            content=pdf_data,
            dt=doc.doctype,
            dn=doc.name,
            is_private=0
        )
        file_url = get_url(_file.file_url)
        print(f"[WhatsApp] 📂 File saved at: {file_url}")

        # Extract month and year from start_date
        try:
            start_date = frappe.utils.getdate(doc.start_date)
            start_month = start_date.strftime("%B")
            year = start_date.strftime("%Y")
        except Exception:
            start_month = "Unknown"
            year = "Unknown"

        # WhatsApp API (UltraMsg)
        instance_id = "instance132549"
        token = "2ixk8g8b41f9jp1v"
        api_url = f"https://api.ultramsg.com/{instance_id}/messages/document"

        payload = {
            "token": token,
            "to": whatsapp_number,
            "filename": sanitized_filename,
            "document": file_url,
            "caption": f"Hello {employee.employee_name}, your Salary Slip for {start_month}-{year} is attached."
        }

        print(f"[WhatsApp] 📤 Sending payload to UltraMsg...")
        response = requests.post(api_url, data=payload)

        if response.status_code == 200:
            print(f"[WhatsApp] ✅ Sent successfully: {response.text}")
        else:
            print(f"[WhatsApp] ⚠️ Failed to send: {response.status_code} - {response.text}")

    except Exception:
        print(f"[WhatsApp] ❌ Exception occurred:\n{frappe.get_traceback()}")
