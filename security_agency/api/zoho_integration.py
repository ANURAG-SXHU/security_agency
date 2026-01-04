import frappe
import requests
from frappe.utils import now
import json

def get_zoho_settings():
    return frappe.get_single("Zoho Settings")


def refresh_access_token():
    """Refresh Zoho access token using saved refresh token"""
    settings = get_zoho_settings()
    url = "https://accounts.zoho.in/oauth/v2/token"

    data = {
        "refresh_token": settings.refresh_token,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "grant_type": "refresh_token"
    }

    response = requests.post(url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        settings.access_token = tokens.get("access_token")
        settings.save()
        frappe.db.commit()
        return settings.access_token
    else:
        frappe.log_error(response.text, "Zoho Token Refresh Failed")
        frappe.throw("Zoho token refresh failed")


def get_access_token():
    """Always get valid token"""
    settings = get_zoho_settings()
    if not settings.access_token:
        return refresh_access_token()
    return settings.access_token


@frappe.whitelist()
def fetch_and_save_zoho_customers():
    """Fetch customers from Zoho Books & save to local table"""
    settings = get_zoho_settings()
    access_token = get_access_token()
    org_id = settings.org_id
    base_url = "https://www.zohoapis.in/books/v3"

    url = f"{base_url}/contacts"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "X-com-zoho-books-organizationid": org_id
    }

    response = requests.get(url, headers=headers)

    # 🗝️ Auto-refresh if expired
    if response.status_code == 401:
        access_token = refresh_access_token()
        headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
        response = requests.get(url, headers=headers)

    if response.status_code != 200:
        frappe.throw(f"Failed to fetch customers: {response.text}")

    customers = response.json().get("contacts", [])
    inserted, skipped, failed = 0, 0, 0

    for cust in customers:
        try:
            customer_name = cust.get("contact_name")
            zoho_id = cust.get("contact_id")
            company_name = cust.get("company_name")
            email = cust.get("email")
            phone = cust.get("phone")
            gstin = cust.get("gst_treatment")
            place = cust.get("place_of_contact") or cust.get("billing_address", {}).get("state")

            if frappe.db.exists("Zoho Customer", {"zoho_customer_id": zoho_id}) or \
               frappe.db.exists("Zoho Customer", {"customer_name": customer_name}):
                skipped += 1
                continue

            frappe.get_doc({
                "doctype": "Zoho Customer",
                "zoho_customer_id": zoho_id,
                "customer_name": customer_name,
                "company_name": company_name,
                "email": email,
                "phone": phone,
                "gstin": gstin,
                "place_of_supply": place
            }).insert(ignore_permissions=True)
            inserted += 1

        except Exception:
            failed += 1
            frappe.log_error(frappe.get_traceback(), f"Zoho Customer Insert Failed for {customer_name}")

    settings.last_synced = now()
    settings.save()

    return f"Fetched: {len(customers)} | Inserted: {inserted} | Skipped: {skipped} | Failed: {failed}"

@frappe.whitelist(allow_guest=True)
def my_auth_callback(code=None):
    if not code:
        frappe.throw("Missing code parameter")

    client_id = frappe.db.get_single_value("Zoho Settings", "client_id")
    client_secret = frappe.db.get_single_value("Zoho Settings", "client_secret")
    redirect_uri = "https://erpmtss.m.frappe.cloud/api/method/security_agency.api.zoho_integration.my_auth_callback"

    url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    }

    response = requests.post(url, data=data)

    frappe.log_error(
        "Zoho OAuth Debug",
        f"Status Code: {response.status_code}\nResponse: {response.text}"
    )

    tokens = response.json()

    if "error" in tokens:
        frappe.throw(f"Zoho OAuth Error: {tokens}")

    frappe.db.set_single_value("Zoho Settings", "access_token", tokens.get("access_token"))
    frappe.db.set_single_value("Zoho Settings", "refresh_token", tokens.get("refresh_token"))

    return {
        "message": "Zoho token received",
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token")
    }


# @frappe.whitelist()
# def push_invoice_to_zoho(name):
#     """Push Work Order Billing invoice to Zoho Books (India domain safe + fallback for PDF)"""

#     import json

#     doc = frappe.get_doc("Work Order Billing", name)

#     # ✅ 1. Get Zoho Customer ID
#     zoho_customer_id = frappe.db.get_value(
#         "Zoho Customer",
#         doc.zoho_customer,
#         "zoho_customer_id"
#     )
#     if not zoho_customer_id:
#         frappe.throw("No Zoho Customer linked!")

#     # ✅ 2. Build line items
#     line_items = []
#     for row in doc.invoice_lines:
#         line_items.append({
#             "name": row.description,
#             "rate": float(row.rate),
#             "quantity": float(row.quantity)
#         })

#     # payload = {
#     #     "customer_id": zoho_customer_id,
#     #     "line_items": line_items
#     # }
#     payload = {
#     "customer_id": zoho_customer_id,
#     "line_items": line_items,
#     "notes": doc.customer_notes or "",
#     "terms": doc.terms_conditions or ""
# }
#     frappe.log_error(json.dumps(payload, indent=2), "🔍 Zoho Invoice Payload")

#     # ✅ 3. Prepare Zoho config
#     settings = get_zoho_settings()
#     access_token = get_access_token()
#     org_id = settings.org_id
#     api_domain = getattr(settings, "api_domain", "https://www.zohoapis.in")

#     if not org_id:
#         frappe.throw("Zoho Settings missing Org ID!")

#     url = f"{api_domain}/books/v3/invoices?organization_id={org_id}"

#     headers = {
#         "Authorization": f"Zoho-oauthtoken {access_token}"
#     }

#     # ✅ 4. POST invoice
#     res = requests.post(url, headers=headers, json=payload)

#     # Refresh & retry if 401
#     if res.status_code == 401:
#         access_token = refresh_access_token()
#         headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
#         res = requests.post(url, headers=headers, json=payload)

#     if res.status_code >= 400:
#         frappe.log_error(res.text, "❌ Zoho Invoice API Error")
#         frappe.throw(f"Zoho API Error: {res.text}")

#     data = res.json()
#     if data.get("code") != 0:
#         frappe.throw(f"Zoho Error: {data}")

#     invoice_id = data["invoice"]["invoice_id"]
#     pdf_url = data["invoice"].get("pdf_url")

#     # ✅ 5. Fallback GET if pdf_url is missing
#     if not pdf_url:
#         get_url = f"{api_domain}/books/v3/invoices/{invoice_id}?organization_id={org_id}"
#         get_res = requests.get(get_url, headers=headers)

#         if get_res.status_code >= 400:
#             frappe.log_error(get_res.text, "❌ Zoho GET Invoice API Error")
#             frappe.msgprint("Invoice pushed, but PDF URL could not be fetched.")
#             pdf_url = ""
#         else:
#             pdf_data = get_res.json()
#             pdf_url = pdf_data.get("invoice", {}).get("pdf_url", "")

#     doc.zoho_invoice_id = invoice_id
#     doc.zoho_invoice_pdf_url = pdf_url
#     doc.save()

#     return f"✅ Pushed to Zoho Books! Invoice ID: {invoice_id}, PDF: {pdf_url or 'Not available'}"


# @frappe.whitelist()
# def push_invoice_to_zoho(name):
#     import json, time

#     doc = frappe.get_doc("Work Order Billing", name)

#     # Step 1: Get Customer ID
#     zoho_customer_id = frappe.db.get_value("Zoho Customer", doc.zoho_customer, "zoho_customer_id")
#     if not zoho_customer_id:
#         frappe.throw("No Zoho Customer linked to this Work Order Billing.")

#     # Step 2: Build line items
#     line_items = []
#     for row in doc.invoice_lines:
#         line_items.append({
#             "name": row.description,
#             "rate": float(row.rate),
#             "quantity": float(row.quantity)
#         })

#     # Step 3: Build payload
#     payload = {
#         "customer_id": zoho_customer_id,
#         "line_items": line_items,
#         "notes": doc.customer_notes or "",
#         "terms": doc.terms_conditions or ""
#     }

#     frappe.log_error(json.dumps(payload, indent=2), "🔍 Zoho Invoice Payload")

#     # Step 4: Setup config
#     settings = get_zoho_settings()
#     access_token = get_access_token()
#     org_id = settings.org_id
#     api_domain = getattr(settings, "api_domain", "https://www.zohoapis.in")

#     headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
#     create_url = f"{api_domain}/books/v3/invoices?organization_id={org_id}"

#     # Step 5: Create invoice
#     res = requests.post(create_url, headers=headers, json=payload)

#     if res.status_code == 401:
#         access_token = refresh_access_token()
#         headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
#         res = requests.post(create_url, headers=headers, json=payload)

#     if res.status_code >= 400:
#         frappe.log_error(res.text, "❌ Zoho Invoice API Error")
#         frappe.throw(f"Zoho API Error: {res.text}")

#     data = res.json()
#     if data.get("code") != 0:
#         frappe.throw(f"Zoho Error: {json.dumps(data)}")

#     invoice_id = data["invoice"]["invoice_id"]
#     pdf_url = data["invoice"].get("pdf_url", "")

#     # Step 6: Conditionally trigger email to generate PDF
#     if not pdf_url and doc.send_invoice_email_to_generate_pdf:
#         send_url = f"{api_domain}/books/v3/invoices/{invoice_id}/email?organization_id={org_id}"
#         email_payload = {
#             "send_from_org_email_id": True,
#             "to_mail_ids": [frappe.db.get_value("Zoho Customer", doc.zoho_customer, "email") or "dummy@example.com"],
#             "subject": "Invoice from your vendor",
#             "body": "Please find the invoice attached."
#         }
#         send_res = requests.post(send_url, headers=headers, json=email_payload)
#         time.sleep(2)

#         # Step 7: Fetch updated invoice
#         get_url = f"{api_domain}/books/v3/invoices/{invoice_id}?organization_id={org_id}"
#         get_res = requests.get(get_url, headers=headers)

#         if get_res.status_code == 200:
#             invoice_data = get_res.json().get("invoice", {})
#             pdf_url = invoice_data.get("pdf_url", "")
#         else:
#             frappe.log_error(get_res.text, "❌ Zoho GET Invoice API Error")

#     # Step 8: Save to Work Order Billing
#     doc.zoho_invoice_id = invoice_id
#     doc.zoho_invoice_pdf_url = pdf_url
#     doc.save(ignore_permissions=True)

#     return f"✅ Pushed to Zoho Books! Invoice ID: {invoice_id}, PDF: {pdf_url or 'Not available'}"


@frappe.whitelist()
def push_invoice_to_zoho(name):
    import json, time
    import requests

    doc = frappe.get_doc("Work Order Billing", name)

    # Step 1: Get Zoho Customer ID
    zoho_customer_id = frappe.db.get_value("Zoho Customer", doc.zoho_customer, "zoho_customer_id")
    if not zoho_customer_id:
        frappe.throw("No Zoho Customer linked to this Work Order Billing.")

    # Step 2: Fetch Zoho Customer info
    zoho_customer = frappe.get_doc("Zoho Customer", doc.zoho_customer)
    customer_state = (zoho_customer.place_of_supply or "").strip().upper()

    COMPANY_STATE = "OD"  # Your state code (Odisha)

    # Tax component IDs
    CGST_ID = "2441536000000037039"
    OGST_ID = "2441536000000037045"
    IGST_ID = "2441536000000030382"

    # Account ID for revenue
    ACCOUNT_ID = "2441536000000000486"

    # Decide which tax ids to apply
    if customer_state == COMPANY_STATE:
        tax_ids_to_apply = [CGST_ID, IGST_ID]
    else:
        tax_ids_to_apply = [IGST_ID]

    # Step 3: Build line items
    line_items = []
    for row in doc.invoice_lines:
        line_items.append({
            "description": row.description,
            "rate": float(row.rate),
            "quantity": float(row.quantity),
            "account_id": ACCOUNT_ID,
            "tax_ids": tax_ids_to_apply
        })

    # Step 4: Build payload
    payload = {
        "customer_id": zoho_customer_id,
        "place_of_supply": customer_state or COMPANY_STATE,
        "gst_treatment": "business_gst",
        "line_items": line_items,
        "notes": doc.customer_notes or "",
        "terms": doc.terms_conditions or ""
    }

    frappe.log_error(json.dumps(payload, indent=2), "🔍 Zoho Invoice Payload")

    # Step 5: Setup API call
    settings = get_zoho_settings()
    access_token = get_access_token()
    org_id = settings.org_id
    api_domain = getattr(settings, "api_domain", "https://www.zohoapis.in")

    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    create_url = f"{api_domain}/books/v3/invoices?organization_id={org_id}"

    # Step 6: Create invoice
    res = requests.post(create_url, headers=headers, json=payload)
    if res.status_code == 401:
        access_token = refresh_access_token()
        headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
        res = requests.post(create_url, headers=headers, json=payload)

    if res.status_code >= 400:
        frappe.log_error(res.text, "❌ Zoho Invoice API Error")
        frappe.throw(f"Zoho API Error: {res.text}")

    data = res.json()
    if data.get("code") != 0:
        frappe.throw(f"Zoho Error: {json.dumps(data)}")

    invoice_id = data["invoice"]["invoice_id"]
    pdf_url = data["invoice"].get("pdf_url", "")

    # Step 7: Save results
    doc.zoho_invoice_id = invoice_id
    doc.zoho_invoice_pdf_url = pdf_url
    doc.save(ignore_permissions=True)

    return f"✅ Pushed to Zoho Books Successfully! Invoice ID: {invoice_id}, PDF: {pdf_url or 'Not available'}"
