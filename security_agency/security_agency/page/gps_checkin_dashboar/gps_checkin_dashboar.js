frappe.pages['gps-checkin-dashboar'].on_page_load = function(wrapper) {

    console.log("🚀 gps-checkin-dashboar page JS loaded");

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'GPS Check-in Dashboard',
        single_column: true
    });

    // Render the HTML template
    $(frappe.render_template("gps_checkin_dashboar", {})).appendTo(page.body);

    let chartSite = null;
    let chartLast7 = null;

    // Load Chart.js
    $.getScript("https://cdn.jsdelivr.net/npm/chart.js", function () {
        load_site_filter();
        set_default_date();
        load_dashboard();
    });

    // 🔥 Load Site dropdown from backend
    function load_site_filter() {
        frappe.call({
            method: "security_agency.security_agency.page.gps_checkin_dashboar.gps_checkin_dashboar.get_sites",
            callback: function (r) {
                let sites = r.message || [];
                let select = $("#filter_site");

                sites.forEach(s => {
                    select.append(`<option value="${s.name}">${s.name}</option>`);
                });
            }
        });

        // Bind filter button
        $("#apply_filters").click(function () {
            load_dashboard();
        });
    }

    // Set default date = today
    function set_default_date() {
        $("#filter_date").val(frappe.datetime.get_today());
    }

    // 🔥 Load Dashboard Data
    function load_dashboard() {

        const site = $("#filter_site").val();
        const date = $("#filter_date").val();

        console.log("📡 Sending filters:", site, date);

        frappe.call({
            method: "security_agency.security_agency.page.gps_checkin_dashboar.gps_checkin_dashboar.get_data",
            args: {
                site: site,
                date: date
            },
            callback: function (r) {
                const d = r.message || {};
                console.log("📥 Dashboard Data:", d);

                $('#total_today').text(d.total_today || 0);
                $('#pending').text(d.pending || 0);
                $('#approved').text(d.approved || 0);
                $('#rejected').text(d.rejected || 0);

                // Destroy existing charts before creating new ones
                if (chartSite) chartSite.destroy();
                if (chartLast7) chartLast7.destroy();

                // 🔵 Chart 1 — By Site
                chartSite = new Chart(document.getElementById('chart_by_site').getContext("2d"), {
                    type: 'bar',
                    data: {
                        labels: (d.by_site || []).map(x => x.site),
                        datasets: [{
                            label: 'Check-ins',
                            data: (d.by_site || []).map(x => x.count),
                            backgroundColor: 'rgba(54,162,235,0.6)'
                        }]
                    }
                });

                // 🟢 Chart 2 — Last 7 Days
                chartLast7 = new Chart(document.getElementById('chart_last7').getContext("2d"), {
                    type: 'line',
                    data: {
                        labels: (d.last7 || []).map(x => x.date),
                        datasets: [{
                            label: 'Check-ins',
                            data: (d.last7 || []).map(x => x.count),
                            borderColor: 'rgba(75,192,192,1)',
                            fill: false,
                            tension: 0.1
                        }]
                    }
                });
            }
        });
    }
};
