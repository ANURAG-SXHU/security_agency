import frappe
import requests
from frappe.utils.pdf import get_pdf
from frappe import _

@frappe.whitelist()
def send_salary_slip_pdf_on_whatsapp(docname):
    doc = frappe.get_doc("Salary Slip", docname)
    employee = frappe.get_doc("Employee", doc.employee)

    if not employee.custom_whatsapp_number:
        frappe.throw(_("WhatsApp number not found for employee"))

    pdf_data = get_pdf(doc, print_format="MTSS SALARY SLIP")
    filename = f"{doc.name}.pdf"

    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "is_private": 0,
        "content": pdf_data,
        "attached_to_doctype": doc.doctype,
        "attached_to_name": doc.name
    })
    _file.save()
    file_url = frappe.utils.get_url(_file.file_url)

    instance_id = "instance132549"
    token = "2ixk8g8b41f9jp1v"
    url = f"https://api.ultramsg.com/{instance_id}/messages/document"

    payload = {
        "token": token,
        "to": employee.custom_whatsapp_number,
        "filename": filename,
        "document": file_url,
        "caption": f"Hello {employee.employee_name}, your Salary Slip for {doc.month}-{doc.fiscal_year} is attached."
    }

    res = requests.post(url, data=payload)
    frappe.logger().info(f"UltraMsg response: {res.text}")
