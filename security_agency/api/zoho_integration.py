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



@frappe.whitelist()
def find_invoice_by_reference(reference, org_id, token, api_domain):
    import requests

    headers = {
        "Authorization": f"Zoho-oauthtoken {token}"
    }

    url = f"{api_domain}/books/v3/invoices"
    params = {
        "organization_id": org_id,
        "reference_number": reference
    }

    r = requests.get(url, headers=headers, params=params)
    data = r.json()

    if data.get("code") == 0 and data.get("invoices"):
        return data["invoices"][0]["invoice_id"]

    return None
@frappe.whitelist()
def push_invoice_to_zoho(name):
    """
    Final, safe, idempotent Zoho invoice push
    """

    import json
    import requests
    from frappe.utils import now

    doc = frappe.get_doc("Work Order Billing", name)

    # -------------------------------------------------
    # 0️⃣ HARD IDEMPOTENCY (Already linked)
    # -------------------------------------------------
    if doc.zoho_invoice_id:
        return f"ℹ️ Invoice already exists in Zoho. ID: {doc.zoho_invoice_id}"

    # -------------------------------------------------
    # 1️⃣ CUSTOMER MAPPING
    # -------------------------------------------------
    zoho_customer_id = frappe.db.get_value(
        "Zoho Customer",
        doc.zoho_customer,
        "zoho_customer_id"
    )

    if not zoho_customer_id:
        frappe.throw("No Zoho Customer linked to this Work Order Billing")

    zoho_customer = frappe.get_doc("Zoho Customer", doc.zoho_customer)
    customer_state = (zoho_customer.place_of_supply or "").strip().upper()

    COMPANY_STATE = "OD"  # Odisha

    # -------------------------------------------------
    # 2️⃣ TAX IDS (VERIFIED)
    # -------------------------------------------------
    GST18_TAX_GROUP_ID = "2441536000000030488"   # Intra-state GST 18%
    IGST18_TAX_ID = "2441536000000030386"        # Inter-state IGST 18%

    tax_id = GST18_TAX_GROUP_ID if customer_state == COMPANY_STATE else IGST18_TAX_ID

    # -------------------------------------------------
    # 3️⃣ SALES ACCOUNT
    # -------------------------------------------------
    SALES_ACCOUNT_ID = "2441536000000000486"  # Sales

    # -------------------------------------------------
    # 4️⃣ BUILD LINE ITEMS
    # -------------------------------------------------
    line_items = []
    for row in doc.invoice_lines:
        line_items.append({
            "name": row.description or "Security Services",
            "rate": float(row.rate),
            "quantity": float(row.quantity),
            "account_id": SALES_ACCOUNT_ID,
            "tax_id": tax_id
        })

    if not line_items:
        frappe.throw("No invoice lines found")

    # -------------------------------------------------
    # 5️⃣ PAYLOAD (REFERENCE NUMBER = DOC NAME)
    # -------------------------------------------------
    payload = {
        "customer_id": zoho_customer_id,
        "reference_number": doc.name,   # ⭐ KEY FOR IDEMPOTENCY
        "place_of_supply": customer_state or COMPANY_STATE,
        "line_items": line_items,
        "notes": doc.customer_notes or "",
        "terms": doc.terms_conditions or ""
    }

    frappe.log_error(json.dumps(payload, indent=2), "📤 Zoho Invoice Payload")

    # -------------------------------------------------
    # 6️⃣ API SETUP
    # -------------------------------------------------
    settings = get_zoho_settings()
    access_token = get_access_token()
    org_id = settings.org_id
    api_domain = getattr(settings, "api_domain", "https://www.zohoapis.in")

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    create_url = f"{api_domain}/books/v3/invoices?organization_id={org_id}"

    # -------------------------------------------------
    # 7️⃣ PRE-CHECK: EXISTING INVOICE BY REFERENCE
    # -------------------------------------------------
    existing_invoice_id = find_invoice_by_reference(
        doc.name,
        org_id,
        access_token,
        api_domain
    )

    if existing_invoice_id:
        doc.zoho_invoice_id = existing_invoice_id
        doc.zoho_last_synced = now()
        doc.save(ignore_permissions=True)
        return f"ℹ️ Invoice already existed in Zoho | ID: {existing_invoice_id}"

    # -------------------------------------------------
    # 8️⃣ CREATE INVOICE
    # -------------------------------------------------
    response = requests.post(create_url, headers=headers, json=payload)

    # 🔁 Auto-refresh token
    if response.status_code == 401:
        access_token = refresh_access_token()
        headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
        response = requests.post(create_url, headers=headers, json=payload)

    if response.status_code >= 400:
        frappe.log_error(response.text, "❌ Zoho Invoice HTTP Error")
        frappe.throw(response.text)

    data = response.json()

    # -------------------------------------------------
    # 9️⃣ HANDLE ZOHO ERRORS
    # -------------------------------------------------
    if data.get("code") != 0:

        # Duplicate detected by Zoho (race condition)
        if data.get("code") == 1001:
            invoice_id = find_invoice_by_reference(
                doc.name,
                org_id,
                access_token,
                api_domain
            )
            if invoice_id:
                doc.zoho_invoice_id = invoice_id
                doc.zoho_last_synced = now()
                doc.save(ignore_permissions=True)
                return f"ℹ️ Invoice already existed in Zoho | ID: {invoice_id}"

        frappe.throw(json.dumps(data))

    # -------------------------------------------------
    # 🔟 SAVE SUCCESS
    # -------------------------------------------------
    invoice = data["invoice"]

    doc.zoho_invoice_id = invoice["invoice_id"]
    doc.zoho_invoice_pdf_url = invoice.get("pdf_url")
    doc.zoho_last_synced = now()
    doc.save(ignore_permissions=True)

    return f"✅ Zoho Invoice Created Successfully | ID: {invoice['invoice_id']}"
