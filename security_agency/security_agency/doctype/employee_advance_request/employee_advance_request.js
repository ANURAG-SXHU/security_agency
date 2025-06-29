// Copyright (c) 2025, Anurag Sahu
// For license information, please see license.txt

frappe.ui.form.on('Employee Advance Request', {
    mode_of_payment(frm) {
        const mode = frm.doc.mode_of_payment;

        if (mode === "UPI ID") {
            frm.set_df_property('upi_id', 'hidden', 0);
            frm.set_df_property('upi_id', 'reqd', 1);

            frm.set_df_property('qr', 'hidden', 1);
            frm.set_df_property('qr', 'reqd', 0);

            frm.set_value('qr', null);

        } else if (mode === "QR") {
            frm.set_df_property('upi_id', 'hidden', 1);
            frm.set_df_property('upi_id', 'reqd', 0);

            frm.set_df_property('qr', 'hidden', 0);
            frm.set_df_property('qr', 'reqd', 1);

            frm.set_value('upi_id', null);

        } else {
            frm.set_df_property('upi_id', 'hidden', 1);
            frm.set_df_property('qr', 'hidden', 1);

            frm.set_df_property('upi_id', 'reqd', 0);
            frm.set_df_property('qr', 'reqd', 0);

            frm.set_value('upi_id', null);
            frm.set_value('qr', null);
        }

        frm.refresh_fields(['upi_id', 'qr']);
    },

    onload(frm) {
        // Set default posting date to today
        if (!frm.doc.posting_date) {
            frm.set_value('posting_date', frappe.datetime.get_today());
        }

        // Set employee based on logged-in user if not already filled
        if (!frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Employee",
                    filters: {
                        user_id: frappe.session.user
                    },
                    fields: ["name"]
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value("employee", r.message[0].name);
                    }
                }
            });
        }

        // Apply visibility/mode rules
        frm.trigger('mode_of_payment');
    }
});
