frappe.ui.form.on('Mess Tracker', {
    refresh(frm) {
        if (frm.is_new() || frm.doc.workflow_state !== "Approved") {
            frm.trigger("populate_employee_deductions");
        }
    },

    total_amount(frm) {
        frm.trigger("populate_employee_deductions");
    },

    distribute_mode(frm) {
        frm.trigger("populate_employee_deductions");
    },

    reports_to(frm) {
        frm.trigger("populate_employee_deductions");
    },

    populate_employee_deductions(frm) {
        console.log("Triggering employee deduction population...");

        if (!frm.doc.total_amount) {
            console.log("Missing total_amount");
            return;
        }

        if (frm.doc.distribute_mode !== "Equal") {
            console.log("Distribute mode is not Equal");
            return;
        }

        if (!frm.doc.reports_to) {
            console.log("Missing reports_to");
            return;
        }

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Employee",
                filters: {
                    reports_to: frm.doc.reports_to,
                    status: "Active"
                },
                fields: ["name", "employee_name"]
            },
            callback(r) {
                console.log("Employee fetch response:", r.message);

                if (!r.message || r.message.length === 0) {
                    frappe.msgprint("No employees found reporting to the selected authority.");
                    return;
                }

                let per_head = frm.doc.total_amount / r.message.length;

                frm.clear_table("deduction_table");

                r.message.forEach(emp => {
                    let row = frm.add_child("deduction_table");
                    row.employee = emp.name;
                    row.employee_name = emp.employee_name;
                    row.amount_to_deduct = per_head;
                });

                frm.refresh_field("deduction_table");
            }
        });
    }
});
