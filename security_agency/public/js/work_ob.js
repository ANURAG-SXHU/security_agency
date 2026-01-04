// frappe.ui.form.on("Work Order Billing", {
//     work_order_pdf: function(frm) {
//         if (!frm.doc.work_order_pdf) return;

//         frm.save().then(() => {
//             frappe.show_progress("Extracting", 30, 100, "Extracting Work Order Details...");
//             frappe.call({
//                 method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.extract_work_order_info",
//                 args: { name: frm.doc.name },
//                 callback: function (r) {
//                     frappe.hide_progress();
//                     if (!r.exc) {
//                         frappe.msgprint("✅ Work Order details extracted.");
//                         frm.reload_doc();
//                     } else {
//                         frappe.msgprint("❌ Could not extract Work Order details.");
//                     }
//                 },
//                 error: function (err) {
//                     frappe.hide_progress();
//                     frappe.msgprint("❌ Server error during extraction.");
//                     console.error("PDF Extract Error:", err);
//                 }
//             });
//         });
//     },

//     attendance_xls: function(frm) {
//         if (!frm.doc.attendance_xls) return;

//         frm.save().then(() => {
//             frappe.show_progress("Processing", 20, 100, "Processing Attendance File...");
//             frappe.call({
//                 method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.parse_attendance_xlsx",
//                 args: { name: frm.doc.name },
//                 callback: function (r) {
//                     frappe.hide_progress();
//                     if (!r.exc) {
//                         frappe.msgprint("✅ Attendance processed successfully.");
//                         frm.reload_doc();
//                     } else {
//                         frappe.msgprint("❌ Could not process attendance file.");
//                     }
//                 },
//                 error: function (err) {
//                     frappe.hide_progress();
//                     frappe.msgprint("❌ Server error during attendance parsing.");
//                     console.error("Attendance Error:", err);
//                 }
//             });
//         });
//     },

//     generate_invoice: function(frm) {
//         frappe.msgprint("🧾 Go to Print → Select 'Draft Invoice' format to print invoice.");
//     }
// });
frappe.ui.form.on("Work Order Billing", {
    work_order_pdf: function (frm) {
        if (!frm.doc.work_order_pdf) {
            frappe.msgprint("⚠️ Please attach a Work Order PDF first.");
            return;
        }

        frm.save().then(() => {
            frappe.show_progress("Extracting PDF", 30, 100, "Extracting details from Work Order PDF...");
            frappe.call({
                method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.extract_work_order_info",
                args: { name: frm.doc.name },
                freeze: true,
                callback: function (r) {
                    frappe.hide_progress();
                    if (!r.exc) {
                        frappe.msgprint({
                            title: "Success",
                            indicator: "green",
                            message: "✅ Work Order PDF extracted successfully!"
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint("❌ Could not extract details from the PDF. Please check logs.");
                    }
                },
                error: function (err) {
                    frappe.hide_progress();
                    frappe.msgprint("❌ Server error during PDF extraction. Check browser console for details.");
                    console.error("PDF Extract Error:", err);
                }
            });
        });
    },

    attendance_xls: function (frm) {
        if (!frm.doc.attendance_xls) {
            frappe.msgprint("⚠️ Please attach an Attendance XLS file first.");
            return;
        }

        frm.save().then(() => {
            frappe.show_progress("Processing XLS", 20, 100, "Processing Attendance XLS file...");
            frappe.call({
                method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.parse_attendance_xlsx",
                args: { name: frm.doc.name },
                freeze: true,
                callback: function (r) {
                    frappe.hide_progress();
                    if (!r.exc) {
                        frappe.msgprint({
                            title: "Success",
                            indicator: "green",
                            message: "✅ Attendance XLS processed successfully!"
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint("❌ Could not process Attendance XLS. Please check logs.");
                    }
                },
                error: function (err) {
                    frappe.hide_progress();
                    frappe.msgprint("❌ Server error during Attendance XLS processing. Check browser console for details.");
                    console.error("Attendance XLS Error:", err);
                }
            });
        });
    },

    generate_invoice: function (frm) {
        frappe.msgprint("🧾 Draft Invoice is ready. Go to **Print → Draft Invoice** to preview and print it.");
    },

    refresh: function (frm) {
        frm.add_custom_button("📥 Download Attendance Template", () => {
            frappe.call({
                method: "security_agency.security_agency.doctype.work_order_billing.work_order_billing.download_attendance_template",
                args: { docname: frm.doc.name },
                freeze: true,
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: "Download Ready",
                            indicator: "green",
                            message: "✅ Attendance Template is ready. Download will open in a new tab."
                        });
                        window.open(r.message);
                    } else {
                        frappe.msgprint("⚠️ No file returned. Please check server logs.");
                    }
                },
                error: function (err) {
                    frappe.msgprint("❌ Could not generate template. Check browser console.");
                    console.error("Template Download Error:", err);
                }
            });
        });
    }
});
// frappe.ui.form.on('Work Order Billing', {
//   validate: function(frm) {
//     // Build a map from Charges Breakup table
//     let breakup_map = {};
//     (frm.doc.rate_breakup || []).forEach(row => {
//       if (!row.job_description) return;
//       breakup_map[row.job_description.trim()] = {
//         leave_wages: row.leave_wages || 0,
//         national_and_festival_holidays: row.national_and_festival_holidays || 0,
//         epf: row.epf || 0,
//         esic: row.esic || 0,
//         reliver_charges: row.reliver_charges || 0,
//         service_charges: row.service_charges || 0,
//       };
//     });

//     // Loop through Job Rate Details and calculate amounts
//     (frm.doc.job_rate_details || []).forEach(row => {
//       if (!row.job_description) return;

//       let desc = row.job_description.trim();
//       let breakup = breakup_map[desc] || {};
//       let rate_per_day = flt(row.rate_per_day || 0);

//       row.leave_wages = (rate_per_day * flt(breakup.leave_wages || 0)) / 100;
//       row.national_and_festival_holidays = (rate_per_day * flt(breakup.national_and_festival_holidays || 0)) / 100;
//       row.epf = (rate_per_day * flt(breakup.epf || 0)) / 100;
//       row.esic = (rate_per_day * flt(breakup.esic || 0)) / 100;
//       row.reliver_charges = (rate_per_day * flt(breakup.reliver_charges || 0)) / 100;
//       row.service_charges = (rate_per_day * flt(breakup.service_charges || 0)) / 100;
//     });
//   }
// });
// When form loads or rows change, recalculate all derived amounts






