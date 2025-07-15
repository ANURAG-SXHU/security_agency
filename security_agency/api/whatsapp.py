import frappe
import requests
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file

def send_salary_slip_pdf_on_whatsapp(doc, method=None):
    try:
        frappe.logger().info(f"[WhatsApp] 📌 Hook triggered for Salary Slip: {doc.name}")

        # Get Employee
        employee = frappe.get_doc("Employee", doc.employee)
        frappe.logger().info(f"[WhatsApp] ✅ Found employee: {employee.name}")

        # Check WhatsApp number
        if not employee.custom_whatsapp_number:
            frappe.logger().warn(f"[WhatsApp] ❌ No WhatsApp number for {employee.name}")
            return

        frappe.logger().info(f"[WhatsApp] 📱 Sending to: {employee.custom_whatsapp_number}")

        # Generate PDF from rendered HTML
        html = frappe.get_print(doc.doctype, doc.name, print_format="MTSS SALARY SLIP")
        pdf_data = get_pdf(html)

        # Sanitize filename (remove slashes)
        safe_filename = f"{doc.name.replace('/', '-')}.pdf"
        frappe.logger().info(f"[WhatsApp] 🧾 PDF generated: {safe_filename}")

        # Save the file
        _file = save_file(
            fname=safe_filename,
            content=pdf_data,
            dt=doc.doctype,
            dn=doc.name,
            is_private=0
        )
        file_url = frappe.utils.get_url(_file.file_url)
        frappe.logger().info(f"[WhatsApp] 📂 File saved at: {file_url}")

        # UltraMsg API Details
        instance_id = "instance132549"
        token = "2ixk8g8b41f9jp1v"
        url = f"https://api.ultramsg.com/{instance_id}/messages/document"

        payload = {
            "token": token,
            "to": employee.custom_whatsapp_number,
            "filename": safe_filename,
            "document": file_url,
            "caption": f"Hello {employee.employee_name}, your Salary Slip for {doc.month}-{doc.fiscal_year} is attached."
        }

        frappe.logger().info(f"[WhatsApp] 📤 Sending payload to UltraMsg...")
        res = requests.post(url, data=payload)
        frappe.logger().info(f"[WhatsApp] ✅ UltraMsg response: {res.status_code} - {res.text}")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "[WhatsApp] ❌ Failed to send salary slip")
        frappe.logger().error(f"[WhatsApp] ❌ Exception occurred:\n{frappe.get_traceback()}")
