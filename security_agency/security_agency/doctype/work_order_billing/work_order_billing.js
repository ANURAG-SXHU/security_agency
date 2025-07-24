// frappe.ui.form.on("Work Order Billing", {
//     work_order_pdf: function(frm) {
//         if (frm.doc.work_order_pdf) {
//             frappe.call({
//                 method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.extract_work_order_info",
//                 args: { name: frm.doc.name },
//                 callback: function(r) {
//                     if (!r.exc) {
//                         frappe.msgprint("✅ Work Order details extracted via AI.");
//                         frm.reload_doc();
//                     }
//                 }
//             });
//         }
//     },

//     attendance_xls: function(frm) {
//         if (frm.doc.attendance_xls) {
//             frappe.call({
//                 method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.parse_attendance_xlsx",
//                 args: { name: frm.doc.name },
//                 callback: function(r) {
//                     if (!r.exc) {
//                         frappe.msgprint("✅ Attendance processed and table populated.");
//                         frm.reload_doc();
//                     }
//                 }
//             });
//         }
//     },

//     generate_invoice: function(frm) {
//         frappe.msgprint("🧾 Go to Print → Draft Invoice format to print.");
//     }
// });
frappe.ui.form.on('Work Order Billing', {
    refresh(frm) {
        frm.add_custom_button("Download Attendance Template", () => {
            frappe.call({
                method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.download_attendance_template",
                args: {
                    docname: frm.doc.name
                },
                callback(r) {
                    if (r.message) {
                        window.open(r.message);
                    }
                }
            });
        });
    }
});
frappe.ui.form.on('Work Order Billing', {
    push_to_zoho: function(frm) {
        frappe.call({
            method: "security_agency.api.zoho_integration.push_invoice_to_zoho",
            args: { name: frm.doc.name },
            callback: function(r) {
                frappe.msgprint(r.message);
                frm.reload_doc();
            }
        });
    }
});

