frappe.ui.form.on("Work Order Billing", {
    work_order_pdf: function(frm) {
        if (!frm.doc.work_order_pdf) return;

        frm.save().then(() => {
            frappe.show_progress("Extracting", 30, 100, "Extracting Work Order Details...");
            frappe.call({
                method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.extract_work_order_info",
                args: { name: frm.doc.name },
                callback: function (r) {
                    frappe.hide_progress();
                    if (!r.exc) {
                        frappe.msgprint("✅ Work Order details extracted.");
                        frm.reload_doc();
                    } else {
                        frappe.msgprint("❌ Could not extract Work Order details.");
                    }
                },
                error: function (err) {
                    frappe.hide_progress();
                    frappe.msgprint("❌ Server error during extraction.");
                    console.error("PDF Extract Error:", err);
                }
            });
        });
    },

    attendance_xls: function(frm) {
        if (!frm.doc.attendance_xls) return;

        frm.save().then(() => {
            frappe.show_progress("Processing", 20, 100, "Processing Attendance File...");
            frappe.call({
                method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.parse_attendance_xlsx",
                args: { name: frm.doc.name },
                callback: function (r) {
                    frappe.hide_progress();
                    if (!r.exc) {
                        frappe.msgprint("✅ Attendance processed successfully.");
                        frm.reload_doc();
                    } else {
                        frappe.msgprint("❌ Could not process attendance file.");
                    }
                },
                error: function (err) {
                    frappe.hide_progress();
                    frappe.msgprint("❌ Server error during attendance parsing.");
                    console.error("Attendance Error:", err);
                }
            });
        });
    },

    generate_invoice: function(frm) {
        frappe.msgprint("🧾 Go to Print → Select 'Draft Invoice' format to print invoice.");
    }
});
