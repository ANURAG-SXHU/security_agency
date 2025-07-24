// Copyright (c) 2025, Anurag Sahu and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Zoho Customer", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Zoho Customer', {
    refresh(frm) {
        frm.add_custom_button("Sync Zoho Customers", function () {
            frappe.call({
                method: 'security_agency.api.zoho_integration.fetch_and_save_zoho_customers',
                callback: function (r) {
                    frappe.msgprint(r.message);
                }
            });
        });
    }
});
