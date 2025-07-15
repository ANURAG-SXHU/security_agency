// Copyright (c) 2025, Anurag Sahu and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Deployment Sheet", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Deployment Sheet', {
    week_start_date(frm) {
        if (frm.doc.week_start_date) {
            let start = frappe.datetime.add_days(frm.doc.week_start_date, 6);
            frm.set_value('week_end_date', start);
        }
    }
});
