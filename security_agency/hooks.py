app_name = "security_agency"
app_title = "Security Agency"
app_publisher = "Anurag Sahu"
app_description = "this is a securty agency app"
app_email = "theanurag121@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "security_agency",
# 		"logo": "/assets/security_agency/logo.png",
# 		"title": "Security Agency",
# 		"route": "/security_agency",
# 		"has_permission": "security_agency.api.permission.has_app_permission"
# 	}
# ]
app_include_js = [
    "https://unpkg.com/leaflet@1.9.3/dist/leaflet.js",
    "/assets/security_agency/js/planned_visit.js"
]

app_include_css = [
    "https://unpkg.com/leaflet@1.9.3/dist/leaflet.css"
]

fixtures = [
    {"doctype": "Workspace"},
    {"doctype": "Workflow"},
    {"doctype": "Workflow State"},
    {"doctype": "Workflow Action Master"},
    {"doctype": "Role", "filters": [["role_name", "in", ["Guard", "Supervisor", "Field Officer"]]]},
    # 👇 Add this block
    # {
    #     "doctype": "DocType",
    #     "filters": [
    #         ["name", "in", ["Bulk Site Salary Slip Tool"]]
    #     ]
    # }
]


home_page = "app/operations-module"

app_include_js = [
    "/assets/security_agency/js/logo_redirect.js",
    "/assets/security_agency/js/custom_loader.js",
    "/assets/security_agency/js/employee_group.js",
    "/assets/security_agency/js/work_ob.js",
    "/assets/security_agency/js/planned_visit.js",
    "/assets/security_agency/js/guard_attendance_dashboard.js",
    "/assets/security_agency/js/hide_sidebar.js"
    # "/assets/security_agency/js/custom_workspace.js",
    # "/assets/security_agency/js/role_based_ui.js"
]

app_include_css = [
    "/assets/security_agency/css/custom.css",
    "/assets/security_agency/css/custom_home.css",
    "/assets/security_agency/css/shift_calendar_print.css"
    # "/assets/security_agency/css/custom_workspace.css"
]

web_include_css = [
    # "/assets/security_agency/css/custom_home.css"
]
# scheduler_events = {
#     "daily": [
#         "security_agency.security_agency.Tender_reminder.send_tender_reminders",
#         "security_agency.security_agency.attendance_anomaly.mark_daily_anomalies_for_all_sites"
#     ],
#     "hourly": [
#         "security_agency.api.zoho_integration.refresh_access_token",
#         "security_agency.api.zoho_integration.fetch_and_save_zoho_customers"
#     ]
# }
scheduler_events = {
    "daily": [
        "security_agency.security_agency.Tender_reminder.send_tender_reminders",
        "security_agency.security_agency.attendance_anomaly.mark_daily_anomalies_for_all_sites"
    ],

    "hourly": [
        "security_agency.api.zoho_integration.refresh_access_token",
        "security_agency.api.zoho_integration.fetch_and_save_zoho_customers"
    ],

    # 🔹 Run this every 15th of the month at midnight (00:00)
    "cron": {
        "0 0 15 * *": [
            "security_agency.security_agency.custom_hooks.update_regular_shifts_by_month_days"
        ]
    }
}

# For whitelisting the API call
# override_whitelisted_methods = {
#     "security_agency.api.dashboard.get_guard_attendance_summary": "security_agency.api.dashboard.get_guard_attendance_summary"
# }
# Keep your existing API override here
override_whitelisted_methods = {
    "security_agency.api.dashboard.get_guard_attendance_summary":
        "security_agency.api.dashboard.get_guard_attendance_summary"
}

# ✅ Add this new section for Attendance class override
override_doctype_class = {
    "Attendance": "security_agency.security_agency.attendance_override.CustomAttendance"
}



doc_events = {
    "Employee": {
        "after_insert": "security_agency.security_agency.Employee.after_insert_employee"
    },
    "Salary Slip": {
        "before_save": [
            "security_agency.security_agency.custom_hooks.joining_fee_deduction",
            "security_agency.security_agency.custom_hooks.advance_request_deduction",
            "security_agency.security_agency.custom_hooks.mess_deduction",
            "security_agency.security_agency.custom_hooks.add_overtime_from_gps"
        ],
        "on_submit": "security_agency.api.whatsapp.send_salary_slip_pdf_on_whatsapp"
    }
}


# fixed some errror

permission_query_conditions = {
    "GPS Check-in Request": "security_agency.security_agency.doctype.gps_check_in_request.gps_check_in_request.get_permission_query_conditions",
    "Check-In Request GPS": "security_agency.security_agency.doctype.check_in_request_gps.check_in_request_gps.get_permission_query_conditions",
    "Employee": "security_agency.security_agency.doctype.gps_check_in_request.gps_check_in_request.get_employee_permission_query_conditions",
    "Attendance": "security_agency.security_agency.doctype.gps_check_in_request.gps_check_in_request.get_attendance_permission_query_conditions"
}

has_permission = {
    "GPS Check-in Request": "security_agency.security_agency.doctype.gps_check_in_request.gps_check_in_request.has_permission",
    "Check-In Request GPS": "security_agency.security_agency.doctype.check_in_request_gps.check_in_request_gps.has_permission",
    "Employee": "security_agency.security_agency.doctype.gps_check_in_request.gps_check_in_request.has_employee_permission",
    "Attendance": "security_agency.security_agency.doctype.gps_check_in_request.gps_check_in_request.has_attendance_permission"
}





# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/security_agency/css/security_agency.css"
# app_include_js = "/assets/security_agency/js/security_agency.js"

# include js, css files in header of web template
# web_include_css = "/assets/security_agency/css/security_agency.css"
# web_include_js = "/assets/security_agency/js/security_agency.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "security_agency/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "security_agency/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "security_agency.utils.jinja_methods",
# 	"filters": "security_agency.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "security_agency.install.before_install"
# after_install = "security_agency.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "security_agency.uninstall.before_uninstall"
# after_uninstall = "security_agency.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "security_agency.utils.before_app_install"
# after_app_install = "security_agency.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "security_agency.utils.before_app_uninstall"
# after_app_uninstall = "security_agency.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "security_agency.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"security_agency.tasks.all"
# 	],
# 	"daily": [
# 		"security_agency.tasks.daily"
# 	],
# 	"hourly": [
# 		"security_agency.tasks.hourly"
# 	],
# 	"weekly": [
# 		"security_agency.tasks.weekly"
# 	],
# 	"monthly": [
# 		"security_agency.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "security_agency.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "security_agency.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "security_agency.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["security_agency.utils.before_request"]
# after_request = ["security_agency.utils.after_request"]

# Job Events
# ----------
# before_job = ["security_agency.utils.before_job"]
# after_job = ["security_agency.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"security_agency.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

