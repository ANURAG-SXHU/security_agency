frappe.ui.form.on('Planned Visit', {
    refresh(frm) {
        frm.fields_dict.visits.grid.get_field('map_view').df.on_make = function(field) {
            const wrapper = field.$wrapper.get(0);
            const row = field.doc;

            const map_id = `map-${row.idx}-${frappe.utils.get_random(5)}`;
            wrapper.innerHTML = `<div id="${map_id}" style="height: 300px; border: 1px solid #ccc;"></div>`;

            const map = L.map(map_id).setView([20.2961, 85.8245], 7);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

            let marker;

            function setMarker(lat, lng) {
                if (marker) {
                    marker.setLatLng([lat, lng]);
                } else {
                    marker = L.marker([lat, lng], { draggable: true }).addTo(map);
                    marker.on('dragend', function(e) {
                        const pos = e.target.getLatLng();
                        row.latitude = pos.lat;
                        row.longitude = pos.lng;
                        frm.fields_dict.visits.grid.refresh();
                    });
                }
            }

            if (row.latitude && row.longitude) {
                map.setView([row.latitude, row.longitude], 15);
                setMarker(row.latitude, row.longitude);
            }

            map.on('click', function(e) {
                const { lat, lng } = e.latlng;
                setMarker(lat, lng);
                row.latitude = lat;
                row.longitude = lng;
                frm.fields_dict.visits.grid.refresh();
            });
        };
    }
});
