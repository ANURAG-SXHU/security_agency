frappe.pages['gps-checkin-dashboar'].on_page_load = function(wrapper) {
    console.log("🚀 gps-checkin-dashboar page JS loaded");

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'GPS Check-in Dashboard',
        single_column: true
    });

    // render the HTML template
    $(frappe.render_template("gps_checkin_dashboar", {})).appendTo(page.body);

    // ✅ load Chart.js from CDN instead of frappe assets
    $.getScript("https://cdn.jsdelivr.net/npm/chart.js", function() {
        console.log("Chart.js loaded from CDN, calling backend...");
        load_dashboard();
    });

    function load_dashboard() {
        console.log("Calling get_data...");
        frappe.call({
            method: "security_agency.security_agency.page.gps_checkin_dashboar.gps_checkin_dashboar.get_data",
            callback: function(r) {
                console.log("Response from get_data:", r);
                const d = r.message || {};
                $('#total_today').text(d.total_today || 0);
                $('#pending').text(d.pending || 0);
                $('#approved').text(d.approved || 0);
                $('#rejected').text(d.rejected || 0);

                new Chart(document.getElementById('chart_by_site'), {
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

                new Chart(document.getElementById('chart_last7'), {
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
