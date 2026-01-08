frappe.pages['shift-calendar'].on_page_load = function (wrapper) {
    frappe.require(
        ['https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js'],
        () => init_page(wrapper)
    );
};

function init_page(wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Shift Calendar',
        single_column: true
    });

    // ---------------- FILTERS ----------------
    const site = page.add_field({
        fieldtype: 'Link',
        label: 'Site',
        fieldname: 'site',
        options: 'Site',
        reqd: 1
    });

    const month = page.add_field({
        fieldtype: 'Date',
        label: 'Month',
        fieldname: 'month',
        reqd: 1,
        default: frappe.datetime.month_start()
    });

    // ---------------- BUTTONS ----------------
    page.add_button('Table View', load_table);
    page.add_button('Calendar View', load_calendar);
    page.add_button('Print', () => window.print());

    page.add_button('Export Excel', () => {
        if (!site.get_value() || !month.get_value()) {
            frappe.msgprint('Please select Site and Month');
            return;
        }

        const url =
            '/api/method/security_agency.security_agency.page.shift_calendar.shift_calendar.export_shift_calendar_excel'
            + '?site=' + encodeURIComponent(site.get_value())
            + '&month=' + encodeURIComponent(month.get_value());

        window.open(url);
    });

    // ---------------- CONTAINERS ----------------
    const table_container = $('<div></div>').appendTo(page.body);

    const calendar_container = $('<div id="calendar"></div>')
        .css({ minHeight: '700px' })
        .hide()
        .appendTo(page.body);

    let calendar = null;

    // ---------------- DATA FETCH (SAFE) ----------------
    function get_data(callback) {
        if (!site.get_value() || !month.get_value()) {
            callback([]);
            return;
        }

        frappe.call({
            method: 'security_agency.security_agency.page.shift_calendar.shift_calendar.get_shift_calendar',
            args: {
                site: site.get_value(),
                month: month.get_value()
            },
            callback: r => callback(r.message || [])
        });
    }

    // ---------------- TABLE VIEW ----------------
    function load_table() {
        calendar_container.hide();
        table_container.show().empty();

        if (!site.get_value() || !month.get_value()) {
            frappe.msgprint('Please select Site and Month');
            return;
        }

        get_data(data => {
            if (!data.length) {
                table_container.html(
                    '<div class="text-muted">No shifts found for selected month</div>'
                );
                return;
            }

            let html = `
                <table class="table table-bordered table-sm">
                    <thead>
                        <tr>
                            <th>Guard</th>
                            <th>Date</th>
                            <th>Shift</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            data.forEach(r => {
                html += `
                    <tr>
                        <td>${r.guard}</td>
                        <td>${r.date}</td>
                        <td>${r.shift}</td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            table_container.html(html);
        });
    }

    // ---------------- CALENDAR VIEW ----------------
    function load_calendar() {
        table_container.hide();
        calendar_container.show();

        if (!site.get_value() || !month.get_value()) {
            frappe.msgprint('Please select Site and Month');
            return;
        }

        const month_start = moment(month.get_value())
            .startOf('month')
            .toDate();

        const m = moment(month_start);
        page.set_title(`Shift Calendar - ${m.format('MMMM YYYY')}`);

        get_data(data => {

            console.log('🟢 Calendar backend data:', data);

            if (!data.length) {
                calendar_container.html(
                    `<div class="text-muted">
                        No shifts found for ${m.format('MMMM YYYY')}
                    </div>`
                );
                return;
            }

            const shiftColors = {
                "A SHIFT": "#28a745",
                "B SHIFT": "#007bff",
                "C SHIFT": "#6f42c1"
            };

            const events = data.map(r => {
                let color = "#343a40";

                Object.keys(shiftColors).forEach(shift => {
                    if (r.shift && r.shift.includes(shift)) {
                        color = shiftColors[shift];
                    }
                });

                return {
                    title: `${r.guard} (${r.shift})`,
                    start: moment(r.date, 'YYYY-MM-DD').toDate(),
                    allDay: true,
                    backgroundColor: color,
                    borderColor: color,
                    textColor: "#ffffff"
                };
            });

            if (calendar) {
                calendar.destroy();
                calendar = null;
            }

            setTimeout(() => {
                calendar = new FullCalendar.Calendar(calendar_container[0], {
                    initialView: 'dayGridMonth',
                    initialDate: month_start,

                    headerToolbar: false,
                    showNonCurrentDates: false,
                    fixedWeekCount: false,

                    height: 700,
                    events: events
                });

                calendar.render();
                calendar.gotoDate(month_start);
            }, 50);
        });
    }

    // ---------------- AUTO RELOAD ----------------
    month.$input.on('change', () => {
        if (calendar_container.is(':visible') && site.get_value()) {
            load_calendar();
        }
    });

    // ---------------- DEFAULT ----------------
    load_table();
}
