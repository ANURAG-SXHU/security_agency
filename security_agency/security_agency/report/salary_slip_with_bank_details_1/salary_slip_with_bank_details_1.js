// Copyright (c) 2025, Anurag Sahu and contributors
// For license information, please see license.txt

// frappe.query_reports["Salary Slip with Bank Details 1"] = {
// 	"filters": [
// 		{
// 			"fieldname": "month",
// 			"label": "Month",
// 			"fieldtype": "Select",
// 			"options": [
// 				"January",
// 				"February",
// 				"March",
// 				"April",
// 				"May",
// 				"June",
// 				"July",
// 				"August",
// 				"September",
// 				"October",
// 				"November",
// 				"December"
// 			],
// 			"default": frappe.datetime.str_to_obj(frappe.datetime.nowdate()).toLocaleString('default', { month: 'long' }),
// 			"reqd": 1
// 		},
// 		{
// 			"fieldname": "year",
// 			"label": "Year",
// 			"fieldtype": "Int",
// 			"default": new Date().getFullYear(),
// 			"reqd": 1
// 		}
// 	]
// };
frappe.query_reports["Salary Slip with Bank Details 1"] = {
    "filters": [
        {
            "fieldname": "month",
            "label": __("Month"),
            "fieldtype": "Select",
            "options": "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
            "default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).toLocaleString('default',{ month:'long' })
        },
        {
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Int",
            "default": new Date().getFullYear()
        },
        {
            "fieldname": "site",
            "label": __("Site"),
            "fieldtype": "Link",
            "options": "Site",
            "bold": 1
        }
    ]
};

