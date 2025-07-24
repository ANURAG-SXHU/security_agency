# import frappe
# import requests
# from frappe.utils import now

# def get_zoho_settings():
#     return frappe.get_single("Zoho Settings")

# def refresh_access_token():
#     settings = get_zoho_settings()
#     url = "https://accounts.zoho.in/oauth/v2/token"

#     data = {
#         "refresh_token": settings.refresh_token,
#         "client_id": settings.client_id,
#         "client_secret": settings.client_secret,
#         "grant_type": "refresh_token"
#     }

#     response = requests.post(url, data=data)
#     if response.status_code == 200:
#         tokens = response.json()
#         settings.access_token = tokens.get("access_token")
#         settings.save()
#         return settings.access_token
#     else:
#         frappe.log_error(response.text, "Zoho Token Refresh Failed")
#         frappe.throw("Zoho token refresh failed")

# def get_access_token():
#     settings = get_zoho_settings()
#     if not settings.access_token:
#         return refresh_access_token()
#     return settings.access_token

# @frappe.whitelist()
# def fetch_and_save_zoho_customers():
#     settings = get_zoho_settings()
#     access_token = get_access_token()
#     base_url = frappe.conf.get("zoho_base_url", "https://www.zohoapis.in/books/v3")
#     org_id = settings.org_id

#     url = f"{base_url}/contacts"
#     headers = {
#         "Authorization": f"Zoho-oauthtoken {access_token}",
#         "X-com-zoho-books-organizationid": org_id
#     }

#     response = requests.get(url, headers=headers)
#     if response.status_code == 401:
#         # Token expired, try refreshing
#         access_token = refresh_access_token()
#         headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
#         response = requests.get(url, headers=headers)

#     if response.status_code != 200:
#         frappe.throw(f"Failed to fetch customers: {response.text}")

#     customers = response.json().get("contacts", [])
#     inserted, skipped, failed = 0, 0, 0

#     for cust in customers:
#         try:
#             customer_name = cust.get("contact_name")
#             zoho_id = cust.get("contact_id")
#             company_name = cust.get("company_name")
#             email = cust.get("email")
#             phone = cust.get("phone")
#             gstin = cust.get("gst_treatment")
#             place = cust.get("place_of_contact") or cust.get("billing_address", {}).get("state")

#             if frappe.db.exists("Zoho Customer", {"zoho_customer_id": zoho_id}) or \
#                frappe.db.exists("Zoho Customer", {"customer_name": customer_name}):
#                 skipped += 1
#                 continue

#             frappe.get_doc({
#                 "doctype": "Zoho Customer",
#                 "zoho_customer_id": zoho_id,
#                 "customer_name": customer_name,
#                 "company_name": company_name,
#                 "email": email,
#                 "phone": phone,
#                 "gstin": gstin,
#                 "place_of_supply": place
#             }).insert(ignore_permissions=True)
#             inserted += 1
#         except Exception:
#             failed += 1
#             frappe.log_error(frappe.get_traceback(), f"Zoho Customer Insert Failed for {customer_name}")

#     settings.last_synced = now()
#     settings.save()

#     return f"Fetched: {len(customers)} | Inserted: {inserted} | Skipped: {skipped} | Failed: {failed}"
# #https://accounts.zoho.in/oauth/v2/auth?scope=ZohoBooks.contacts.ALL,ZohoBooks.invoices.ALL,ZohoBooks.settings.READ&client_id=1000.BU6U12L8VVBNULT57NUJM7X6NK5X1K&response_type=code&access_type=offline&redirect_uri=http://localhost:8000/api/method/security_agency.api.zoho_integration.my_auth_callback&prompt=consent
# @frappe.whitelist(allow_guest=True)
# def my_auth_callback(code=None):
#     if not code:
#         frappe.throw("Missing code parameter")

#     client_id = frappe.db.get_single_value("Zoho Settings", "client_id")
#     client_secret = frappe.db.get_single_value("Zoho Settings", "client_secret")
#     redirect_uri = "http://localhost:8000/api/method/security_agency.api.zoho_integration.my_auth_callback"

#     url = "https://accounts.zoho.in/oauth/v2/token"
#     data = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": redirect_uri,
#         "client_id": client_id,
#         "client_secret": client_secret
#     }

#     response = requests.post(url, data=data)
#     if response.status_code != 200:
#         frappe.throw(f"Failed to exchange code: {response.text}")

#     tokens = response.json()
#     frappe.db.set_single_value("Zoho Settings", "access_token", tokens.get("access_token"))
#     frappe.db.set_single_value("Zoho Settings", "refresh_token", tokens.get("refresh_token"))


#     return {
#         "message": "Zoho token received",
#         "access_token": tokens.get("access_token"),
#         "refresh_token": tokens.get("refresh_token")
#     }


# @frappe.whitelist()
# def push_invoice_to_zoho(name):
#     doc = frappe.get_doc("Work Order Billing", name)

#     # ✅ Get customer ID from linked Zoho Customer
#     zoho_customer_id = frappe.db.get_value(
#         "Zoho Customer",
#         doc.zoho_customer,
#         "zoho_customer_id"
#     )
#     if not zoho_customer_id:
#         frappe.throw("No Zoho Customer linked!")

#     # ✅ Build line items from child table
#     line_items = []
#     for row in doc.invoice_lines:
#         line_items.append({
#             "name": row.description,
#             "rate": row.rate,
#             "quantity": row.quantity
#         })

#     payload = {
#         "customer_id": zoho_customer_id,
#         "line_items": line_items
#     }

#     # ✅ Pull Zoho config from your Single DocType
#     zoho_settings = frappe.get_single("Zoho Settings")
#     access_token = zoho_settings.access_token
#     org_id = zoho_settings.org_id

#     if not access_token or not org_id:
#         frappe.throw("Zoho Settings missing Access Token or Org ID!")

#     headers = {
#         "Authorization": f"Zoho-oauthtoken {access_token}"
#     }

#     url = f"https://books.zoho.in/api/v3/invoices?organization_id={org_id}"

#     res = requests.post(url, headers=headers, json=payload)
#     res.raise_for_status()
#     data = res.json()

#     if data.get("code") != 0:
#         frappe.throw(f"Zoho Error: {data}")

#     invoice_id = data["invoice"]["invoice_id"]
#     pdf_url = data["invoice"]["pdf_url"]

#     # ✅ Save back to your Work Order Billing doc
#     doc.zoho_invoice_id = invoice_id
#     doc.zoho_invoice_pdf_url = pdf_url
#     doc.save()

#     return f"✅ Pushed to Zoho Books! Invoice ID: {invoice_id}"
import frappe
import requests
from frappe.utils import now


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
@frappe.whitelist(allow_guest=True)
def my_auth_callback(code=None):
    if not code:
        frappe.throw("Missing code parameter")

    client_id = frappe.db.get_single_value("Zoho Settings", "client_id")
    client_secret = frappe.db.get_single_value("Zoho Settings", "client_secret")
    redirect_uri = "http://localhost:8000/api/method/security_agency.api.zoho_integration.my_auth_callback"

    url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    }

    response = requests.post(url, data=data)

    # ✅ Log in error log for safety
    frappe.log_error(f"Zoho Token Exchange Debug: {response.status_code} {response.text}", "Zoho OAuth Debug")
    # ✅ Print to console
    print(f"🔑 Zoho Token Exchange Debug: {response.status_code} {response.text}")

    try:
        tokens = response.json()
    except:
        frappe.throw(f"Failed to parse JSON: {response.text}")

    if "error" in tokens:
        frappe.throw(f"Zoho OAuth Error: {tokens}")

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    print(f"🔑 Access Token: {access_token}")
    print(f"🔄 Refresh Token: {refresh_token}")

    frappe.db.set_single_value("Zoho Settings", "access_token", access_token)
    frappe.db.set_single_value("Zoho Settings", "refresh_token", refresh_token)

    return {
        "message": "Zoho token received",
        "access_token": access_token,
        "refresh_token": refresh_token
    }



@frappe.whitelist()
def push_invoice_to_zoho(name):
    """Push Work Order Billing invoice to Zoho Books"""
    doc = frappe.get_doc("Work Order Billing", name)

    zoho_customer_id = frappe.db.get_value(
        "Zoho Customer",
        doc.zoho_customer,
        "zoho_customer_id"
    )
    if not zoho_customer_id:
        frappe.throw("No Zoho Customer linked!")

    line_items = []
    for row in doc.invoice_lines:
        line_items.append({
            "name": row.description,
            "rate": row.rate,
            "quantity": row.quantity
        })

    payload = {
        "customer_id": zoho_customer_id,
        "line_items": line_items
    }

    settings = get_zoho_settings()
    access_token = get_access_token()
    org_id = settings.org_id

    if not org_id:
        frappe.throw("Zoho Settings missing Org ID!")

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }

    url = f"https://books.zoho.in/api/v3/invoices?organization_id={org_id}"

    res = requests.post(url, headers=headers, json=payload)

    # 🗝️ Refresh & retry if needed
    if res.status_code == 401:
        access_token = refresh_access_token()
        headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
        res = requests.post(url, headers=headers, json=payload)

    res.raise_for_status()
    data = res.json()

    if data.get("code") != 0:
        frappe.throw(f"Zoho Error: {data}")

    invoice_id = data["invoice"]["invoice_id"]
    pdf_url = data["invoice"]["pdf_url"]

    doc.zoho_invoice_id = invoice_id
    doc.zoho_invoice_pdf_url = pdf_url
    doc.save()

    return f"✅ Pushed to Zoho Books! Invoice ID: {invoice_id}"
