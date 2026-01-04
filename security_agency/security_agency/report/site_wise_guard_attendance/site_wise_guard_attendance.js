// Copyright (c) 2025, Anurag Sahu and contributors
// For license information, please see license.txt

// frappe.query_reports["Site Wise Guard Attendance"] = {
//     "filters": [
//         {
//             fieldname: "site",
//             label: "Site",
//             fieldtype: "Link",
//             options: "Site",
//             reqd: 1
//         },
//         {
//             fieldname: "date",
//             label: "Date",
//             fieldtype: "Date",
//             default: frappe.datetime.get_today(),
//             reqd: 1
//         }
//     ]
// };
frappe.query_reports["Site Wise Guard Attendance"] = {
    "filters": [
        {
            "fieldname": "site",
            "label": "Site",
            "fieldtype": "Link",
            "options": "Site",
            "reqd": 1
        },
        {
            "fieldname": "date",
            "label": "Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        }
    ]
};



