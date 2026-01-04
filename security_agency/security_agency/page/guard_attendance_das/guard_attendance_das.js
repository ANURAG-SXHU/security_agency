frappe.pages['guard-attendance-das'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Guard Attendance Dashboard',
		single_column: true
	});
}