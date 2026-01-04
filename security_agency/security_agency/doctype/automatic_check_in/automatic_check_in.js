// Copyright (c) 2025, Anurag Sahu and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Automatic Check In", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Automatic Check In', {
  refresh: function (frm) {
    const lat = frm.doc.latitude;
    const lng = frm.doc.longitude;

    if (lat && lng) {
      const iframe = `
        <iframe
          width="100%"
          height="300"
          style="border:0"
          loading="lazy"
          allowfullscreen
          referrerpolicy="no-referrer-when-downgrade"
          src="https://www.google.com/maps?q=${lat},${lng}&hl=es;z=14&output=embed">
        </iframe>
      `;
      frm.fields_dict.map_view.$wrapper.html(iframe);
    } else {
      frm.fields_dict.map_view.$wrapper.html('<p style="color: gray;">Location not available</p>');
    }
  }
});
