frappe.pages['guard-attendance-das'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Guard Attendance Dashboard',
        single_column: true
    });

    load_attendance_data(page);
};

function load_attendance_data(page) {
    frappe.call({
        method: 'security_agency.api.dashboard.get_guard_attendance_summary',
        args: { date: frappe.datetime.get_today() },
        callback: function(r) {
            if (r.message && r.message.length) {
                const data = r.message;

                let html = `<table class="table table-bordered">
                    <thead><tr>
                        <th>Site</th>
                        <th>Assigned</th>
                        <th>Present</th>
                        <th>Absent</th>
                        <th>Absent Employees</th>
                    </tr></thead>
                    <tbody>`;

                data.forEach(row => {
                    html += `<tr>
                        <td>${row.site}</td>
                        <td>${row.assigned}</td>
                        <td>${row.present}</td>
                        <td>${row.absent}</td>
                        <td>${row.absent_employees.join(', ')}</td>
                    </tr>`;
                });

                html += `</tbody></table>`;
                page.main.html(html);
            } else {
                page.main.html(`<p>No data found for today.</p>`);
            }
        }
    });
}
