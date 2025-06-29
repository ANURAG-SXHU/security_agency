frappe.ui.form.on("Employee Group", {
    custom_reporting_authority: function (frm) {
        if (!frm.doc.custom_reporting_authority) return;

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Employee",
                filters: {
                    reports_to: frm.doc.custom_reporting_authority
                },
                fields: ["name", "first_name", "user_id"]
            },
            callback: function (r) {
                if (r.message) {
                    // Clear existing entries to avoid duplicates
                    frm.clear_table("employee_list");

                    r.message.forEach(emp => {
                        let row = frm.add_child("employee_list");
                        row.employee = emp.name;
                        row.employee_name = emp.first_name;
                        row.user_id = emp.user_id;
                    });

                    frm.refresh_field("employee_list");
                }
            }
        });
    }
});
