// Copyright (c) 2025, Anurag Sahu and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Guard Shift Rotation", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0) return;

		frm.toggle_reqd("site", true);
		frm.toggle_reqd("day_of_week", true);
		frm.toggle_reqd("rotation_start_date", true);
	},

	fetch_employees(frm) {
		if (!frm.doc.site) {
			frappe.msgprint("Please select Site first");
			return;
		}

		frappe.call({
			method: "fetch_employees",
			doc: frm.doc,
			callback(r) {
				if (r.message !== undefined) {
					frappe.show_alert(
						{ message: `Loaded ${r.message} employees`, indicator: "green" },
						5
					);
					frm.refresh_field("bulk_guard_rotation_employee");
				}
			}
		});
	},

	site(frm) {
		frm.clear_table("bulk_guard_rotation_employee");
		frm.refresh_field("bulk_guard_rotation_employee");
	},

	designation(frm) {
		frm.clear_table("bulk_guard_rotation_employee");
		frm.refresh_field("bulk_guard_rotation_employee");
	},

	employee_status(frm) {
		frm.clear_table("bulk_guard_rotation_employee");
		frm.refresh_field("bulk_guard_rotation_employee");
	},

	before_submit(frm) {
		if (!frm.doc.rotation_template || frm.doc.rotation_template.length === 0) {
			frappe.throw("Please add at least one Rotation Template row");
		}
	}
});
