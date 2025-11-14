// frappe.ui.form.on('Mess Tracker', {
//     // Auto-fill reports_to from session user on new form
//     onload: function(frm) {
//         if (frm.is_new() && !frm.doc.reports_to) {
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Employee",
//                     filters: {
//                         user_id: frappe.session.user
//                     },
//                     fields: ["name"]
//                 },
//                 callback: function(r) {
//                     if (r.message && r.message.length > 0) {
//                         frm.set_value("reports_to", r.message[0].name);
//                     }
//                 }
//             });
//         }
//     },

//     // Fetch subordinates into child table
//     reports_to: function(frm) {
//         if (!frm.doc.reports_to) return;

//         frappe.call({
//             method: "frappe.client.get_list",
//             args: {
//                 doctype: "Employee",
//                 filters: {
//                     reports_to: frm.doc.reports_to
//                 },
//                 fields: ["name", "employee_name"]
//             },
//             callback: function(r) {
//                 if (r.message) {
//                     frm.clear_table("deduction_table");

//                     r.message.forEach(emp => {
//                         let row = frm.add_child("deduction_table");
//                         row.employee = emp.name;
//                         row.employee_name = emp.employee_name;
//                         row.amount_to_deduct = 0;
//                     });

//                     frm.refresh_field("deduction_table");

//                     // Also try distributing after fetching employees
//                     distribute_amount(frm);
//                 }
//             }
//         });
//     },

//     // Trigger auto-distribution on these field changes
//     total_amount: function(frm) {
//         distribute_amount(frm);
//     },

//     distribute_mode: function(frm) {
//         distribute_amount(frm);
//     },

//     month: function(frm) {
//         distribute_amount(frm);
//     }
// });

// // Helper function to distribute total_amount
// function distribute_amount(frm) {
//     if (!frm.doc.distribute_mode || frm.doc.distribute_mode === 'Manual') return;

//     if (!frm.doc.total_amount || frm.doc.total_amount <= 0) return;

//     const rows = frm.doc.deduction_table || [];
//     const total_employees = rows.length;
//     if (total_employees === 0) return;

//     if (frm.doc.distribute_mode === 'Equal') {
//         const amount_per_person = frm.doc.total_amount / total_employees;

//         rows.forEach(row => {
//             row.amount_to_deduct = Math.round(amount_per_person * 100) / 100; // 2 decimal rounding
//         });

//         frm.refresh_field('deduction_table');
//     }
// }
frappe.ui.form.on('Mess Tracker', {

    get_guards: function(frm) {

        if (!frm.doc.reports_to) {
            frappe.msgprint("Please select a Reports To first.");
            return;
        }

        // SAVE FIRST
        frappe.call({
            method: "frappe.desk.form.save.savedocs",
            args: {
                doc: frm.doc,
                action: "Save"
            },
            freeze: true,
            freeze_message: "Saving document...",
            callback: function() {

                // 🔥 MUST RELOAD — mobile needs updated doc
                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Mess Tracker",
                        name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: "Reloading document...",
                    callback: function(res) {

                        let saved_doc = res.message;

                        // NOW FETCH GUARDS
                        frappe.call({
                            method: "frappe.client.get_list",
                            args: {
                                doctype: "Employee",
                                filters: {
                                    reports_to: saved_doc.reports_to,
                                    site: saved_doc.site || undefined
                                },
                                fields: ["name", "employee_name"]
                            },
                            freeze: true,
                            freeze_message: "Fetching guards...",
                            callback: function(r) {

                                frm.clear_table("deduction_table");

                                if (r.message) {
                                    r.message.forEach(emp => {
                                        let row = frm.add_child("deduction_table");
                                        row.employee = emp.name;
                                        row.employee_name = emp.employee_name;
                                        row.amount_to_deduct = 0;
                                    });

                                    frm.refresh_field("deduction_table");
                                }

                                distribute_amount(frm);
                            }
                        });

                    }
                });

            }
        });
    }
});


// -----------------------
// AUTO DISTRIBUTION
// -----------------------
function distribute_amount(frm) {
    if (!frm.doc.distribute_mode || frm.doc.distribute_mode === 'Manual') return;
    if (!frm.doc.total_amount || frm.doc.total_amount <= 0) return;

    const rows = frm.doc.deduction_table || [];
    if (rows.length === 0) return;

    const per = frm.doc.total_amount / rows.length;

    rows.forEach(row => {
        row.amount_to_deduct = Math.round(per * 100) / 100;
    });

    frm.refresh_field("deduction_table");
}
