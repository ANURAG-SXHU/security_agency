import frappe
from frappe.utils import today, add_days, get_datetime

def send_tender_reminders():
    tenders = frappe.get_all(
        "Tender",
        filters={"docstatus": ["<", 2]},
        fields=[
            "name", "owner",
            "submission_date", "submission_reminded",
            "emd_deadline", "emd_reminded",
            "pre_bid_date", "pre_bid_reminded"
        ]
    )

    for tender in tenders:
        doc = frappe.get_doc("Tender", tender.name)
        send = False

        # Reminder for submission date
        if doc.submission_date and not doc.submission_reminded:
            if get_datetime(doc.submission_date) <= add_days(today(), 2):
                send_reminder_email(doc, "Submission Date", doc.submission_date)
                doc.submission_reminded = 1
                send = True

        # Reminder for EMD deadline
        if doc.emd_deadline and not doc.emd_reminded:
            if get_datetime(doc.emd_deadline) <= add_days(today(), 2):
                send_reminder_email(doc, "EMD Deadline", doc.emd_deadline)
                doc.emd_reminded = 1
                send = True

        # Reminder for Pre-Bid meeting
        if doc.pre_bid_date and not doc.pre_bid_reminded:
            if get_datetime(doc.pre_bid_date) <= add_days(today(), 2):
                send_reminder_email(doc, "Pre-Bid Meeting", doc.pre_bid_date)
                doc.pre_bid_reminded = 1
                send = True

        if send:
            doc.save(ignore_permissions=True)

def send_reminder_email(doc, date_type, date_value):
    owner = frappe.get_doc("User", doc.owner)
    if not owner.email:
        return

    subject = f"Tender Reminder: {date_type} for {doc.tender_title or doc.name}"
    message = f"""
Hi {owner.first_name or owner.full_name},

This is a friendly reminder that the **{date_type}** for Tender **{doc.tender_title or doc.name}** is scheduled on **{date_value}**.

Please ensure all necessary actions are completed in time.

Regards,  
Your ERP System
"""
    frappe.sendmail(
        recipients=[owner.email],
        subject=subject,
        message=message
    )
