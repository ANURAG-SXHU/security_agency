frappe.ui.form.on('Bulk Site Salary Slip Tool', {
    onload: function(frm) {
        if (!frm.doc.month || !frm.doc.year) {
            frappe.call({
                method: "security_agency.security_agency.doctype.bulk_site_salary_slip_tool.bulk_site_salary_slip_tool.get_current_month_year",
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("month", r.message.month);
                        frm.set_value("year", r.message.year);
                    }
                }
            });
        }
    },

    get_guards: function(frm) {
        if (!frm.doc.site) {
            frappe.msgprint(__('Please select a Site first.'));
            return;
        }
        frappe.call({
            method: "security_agency.security_agency.doctype.bulk_site_salary_slip_tool.bulk_site_salary_slip_tool.get_guards",
            args: { site: frm.doc.site },
            freeze: true,
            freeze_message: __("Fetching Guards..."),
            callback: function(r) {
                frm.clear_table("bulk_site_salary_slip_employee");
                (r.message || []).forEach(function(emp) {
                    let row = frm.add_child("bulk_site_salary_slip_employee");
                    row.employee = emp.employee;
                    row.employee_name = emp.employee_name;
                });
                frm.refresh_field("bulk_site_salary_slip_employee");
            }
        });
    },

    create_salary_slips: function(frm) {
        if (!frm.doc.month || !frm.doc.year) {
            frappe.msgprint(__('Please select Month and Year.'));
            return;
        }

        // Show progress bar dialog
        let progress_dialog = new frappe.ui.Dialog({
            title: __("Creating & Submitting Salary Slips"),
            fields: [{
                fieldtype: "HTML",
                fieldname: "progress_html",
                options: '<div class="progress"><div class="progress-bar" role="progressbar" style="width:0%">0%</div></div>'
            }]
        });
        progress_dialog.show();

        const update_progress = (current, total) => {
            let percent = total ? (current / total * 100).toFixed(0) : 0;
            progress_dialog.fields_dict.progress_html.$wrapper
                .find('.progress-bar')
                .css('width', percent + '%')
                .text(percent + '%');
        };

        frappe.realtime.on("bulk_salary_progress", function(data) {
            update_progress(data.current, data.total);
            if (data.done) {
                setTimeout(() => progress_dialog.hide(), 1000);
            }
        });

        // Save the form to ensure latest values (month/year) are persisted
        frm.save().then(() => {
            frappe.call({
                method: "security_agency.security_agency.doctype.bulk_site_salary_slip_tool.bulk_site_salary_slip_tool.create_salary_slips",
                args: { docname: frm.doc.name },
                freeze: false,
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: r.message.message
                        });
                    }
                }
            });
        });
    }
});
