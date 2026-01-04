frappe.ui.form.on("Tender", {
    extract_summary: function(frm) {
        frappe.call({
            method: "security_agency.security_agency.doctype.tender.tender.extract_summary",
            args: { name: frm.doc.name },
            callback: function(r) {
                frappe.msgprint(__("Summary extracted successfully"));
                frm.reload_doc();
            }
        });
    },

    ask_ai_for_rate: function(frm) {
        // ✅ No need to save first!
        if (!frm.doc.scope_summary || frm.doc.scope_summary.trim() === "") {
            frappe.msgprint(__("Please fill the Scope Summary before asking for rate."));
            return;
        }

        frappe.call({
            method: "security_agency.security_agency.doctype.tender.tender.ask_ai_for_rate",
            args: { name: frm.doc.name },
            callback: function(r) {
                frappe.msgprint(__("Rate suggestion generated"));
                frm.reload_doc();
            }
        });
    },

    run_prompt: function(frm) {
        // ✅ No need to save first!
        if (!frm.doc.manual_ai_prompt || frm.doc.manual_ai_prompt.trim() === "") {
            frappe.msgprint(__("Please write something in the Manual AI Prompt field."));
            return;
        }

        frappe.call({
            method: "security_agency.security_agency.doctype.tender.tender.run_manual_prompt",
            args: { name: frm.doc.name },
            callback: function(r) {
                frappe.msgprint(__("Manual AI prompt executed"));
                frm.reload_doc();
            }
        });
    }
});

// ✅ Real-time progress updates — keep as is
frappe.realtime.on('textract_progress', (data) => {
    console.log(data.status);
    frappe.show_alert({ message: data.status, indicator: 'blue' });
});
