import frappe
from frappe.utils.password import update_password
from datetime import datetime

def add_user_permission(user, doctype, for_value):
    if not (user and for_value):
        return

    exists = frappe.get_all("User Permission", filters={
        "user": user,
        "allow": doctype,
        "for_value": for_value
    })

    if not exists:
        frappe.get_doc({
            "doctype": "User Permission",
            "user": user,
            "allow": doctype,
            "for_value": for_value,
            "apply_to_all_doctypes": 1,
        }).insert(ignore_permissions=True)
        frappe.msgprint(f"✅ User Permission added for {user} on {doctype} {for_value}")

def create_user_permissions(doc, method):
    user_id = doc.user_id
    reports_to = doc.reports_to

    # Only create permission if supervisor is specified
    if reports_to:
        add_user_permission(user_id, "Employee", reports_to)

# def assign_role_and_set_password(doc, method):
#     user_id = doc.user_id
#     if not user_id:
#         frappe.msgprint("Missing 'user_id'. Cannot assign role or set password.")
#         return

#     # Assign Role based on designation
#     role_map = {
#         "Guard": "Guard",
#         "Supervisor": "Supervisor",
#         "Field Officer": "Field Officer"
#     }

#     role_to_assign = role_map.get(doc.designation)
#     if role_to_assign:
#         try:
#             user = frappe.get_doc("User", user_id)
#             if role_to_assign not in [r.role for r in user.roles]:
#                 user.append("roles", {"role": role_to_assign})
#                 user.save(ignore_permissions=True)
#                 frappe.msgprint(f"Role '{role_to_assign}' assigned to '{user_id}'")
#         except frappe.DoesNotExistError:
#             frappe.log_error(f"User '{user_id}' not found.", "Role Assignment Error")
#             return

#     # Set default password if DOB and name are available
#     if doc.date_of_birth and doc.first_name:
#         try:
#             dob = datetime.strptime(doc.date_of_birth, "%Y-%m-%d").date() if isinstance(doc.date_of_birth, str) else doc.date_of_birth
#             frappe.get_doc("User", user_id)  # confirm existence
#             password_raw = f"{doc.first_name}{dob.strftime('%d%m%Y')}".replace(" ", "")
#             update_password(user_id, password_raw)
#             frappe.msgprint(f"Default password set for '{user_id}': {password_raw}")
#         except Exception as e:
#             frappe.log_error(f"Password not set for {user_id}: {str(e)}", "Password Set Error")
def assign_role_and_set_password(doc, method):
    user_id = doc.user_id
    if not user_id:
        frappe.msgprint("Missing 'user_id'. Cannot assign role or set password.")
        return

    # Assign Role based on designation
    role_map = {
        "Guard": "Guard",
        "Supervisor": "Supervisor",
        "Field Officer": "Field Officer"
    }

    role_to_assign = role_map.get(doc.designation)
    if role_to_assign:
        try:
            user = frappe.get_doc("User", user_id)
            if role_to_assign not in [r.role for r in user.roles]:
                user.append("roles", {"role": role_to_assign})
                user.save(ignore_permissions=True)
                frappe.msgprint(f"Role '{role_to_assign}' assigned to '{user_id}'")
        except frappe.DoesNotExistError:
            frappe.log_error(f"User '{user_id}' not found.", "Role Assignment Error")
            return

    # Set default password for every employee
    try:
        frappe.get_doc("User", user_id)  # confirm user exists
        default_password = "erp@1234"
        update_password(user_id, default_password)
        frappe.msgprint(f"Default password 'erp@1234' set for '{user_id}'")
    except Exception as e:
        frappe.log_error(f"Password not set for {user_id}: {str(e)}", "Password Set Error")

# ✅ Wrapper function to use in hooks.py
def after_insert_employee(doc, method):
    create_user_permissions(doc, method)
    assign_role_and_set_password(doc, method)
