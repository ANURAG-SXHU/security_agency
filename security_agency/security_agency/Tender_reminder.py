import frappe
from frappe.utils import today, add_days

def send_tender_reminders():
    tenders = frappe.get_all("Tender", filters={"docstatus": ["<", 2]}, fields=[
        "name",
        "tender_title",
        "submission_date", "emd_deadline", "pre_bid_date",
        "submission_reminded", "emd_reminded", "pre_bid_reminded",
        "owner"
    ])

    for t in tenders:
        doc = frappe.get_doc("Tender", t.name)

        # Reminder: Submission Date
        if doc.submission_date and not doc.submission_reminded:
            if str(doc.submission_date) == str(add_days(today(), 2)):
                send_reminder_email(doc, "Submission Date", doc.submission_date)
                doc.submission_reminded = 1

        # Reminder: EMD Deadline
        if doc.emd_deadline and not doc.emd_reminded:
            if str(doc.emd_deadline) == str(add_days(today(), 2)):
                send_reminder_email(doc, "EMD Deadline", doc.emd_deadline)
                doc.emd_reminded = 1

        # Reminder: Pre-bid Meeting
        if doc.pre_bid_date and not doc.pre_bid_reminded:
            if str(doc.pre_bid_date) == str(add_days(today(), 2)):
                send_reminder_email(doc, "Pre-bid Meeting", doc.pre_bid_date)
                doc.pre_bid_reminded = 1

        doc.save(ignore_permissions=True)

def send_reminder_email(doc, event_type, event_date):
    subject = f"📌 Reminder: {event_type} for '{doc.tender_title}' on {event_date}"
    message = f"""
Dear User,

This is a reminder that the **{event_type}** for Tender **{doc.tender_title}** is scheduled on **{event_date}**.

Please ensure all necessary submissions or meetings are prepared in time.

Best regards,  
Tender Management System
"""
    frappe.sendmail(
        recipients=[doc.owner],
        subject=subject,
        message=message
    )
