frappe.require('/assets/security_agency/js/exif.js');

frappe.ui.form.on("Check-In Request GPS", {
    onload(frm) {
        // Auto-fill employee from user
        if (!frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user },
                    fields: ["name"]
                },
                callback: (res) => {
                    if (res.message?.length) {
                        frm.set_value("employee", res.message[0].name);
                    }
                }
            });
        }

        // Auto-fetch GPS for new doc
        if (frm.is_new()) {
            requestLocationPermission(frm);
        }

        // Make employee fields read-only for users
        if (frappe.session.user !== 'Administrator') {
            frm.set_df_property('employee', 'read_only', 1);
            frm.set_df_property('reporting_to', 'read_only', 1);
        }
    },

    refresh(frm) {
        // Hide default attach button and inject camera capture
        if (frm.doc.docstatus === 0) {
            frm.fields_dict.upload_selfie.$wrapper.find('.btn-attach').hide();

            if (!frm.fields_dict.upload_selfie.$wrapper.find('.capture-photo-btn').length) {
                frm.fields_dict.upload_selfie.$wrapper.append(`
                    <button class="btn btn-primary btn-sm capture-photo-btn" style="margin-top: 5px;">
                        Capture Photo from Camera
                    </button>
                `);

                frm.fields_dict.upload_selfie.$wrapper.find('.capture-photo-btn').on('click', () => {
                    openNativeCameraOnly(frm);
                });
            }

            frm.add_custom_button('Capture Photo from Camera', () => {
                openNativeCameraOnly(frm);
            });
        }

        if (frm.doc.latitude && frm.doc.longitude) {
            updateMapHTML(frm, frm.doc.latitude, frm.doc.longitude);
        }
    },

    employee(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, 'reports_to')
                .then(r => {
                    if (r.message?.reports_to) {
                        frm.set_value('reporting_to', r.message.reports_to);
                    } else {
                        frm.set_value('reporting_to', '');
                    }
                });
        }
    }
});

// 📍 Fetch location from browser
function requestLocationPermission(frm) {
    if (!navigator.geolocation) {
        frappe.msgprint("Geolocation not supported.");
        frm.set_value('gps_status', 'Unsupported');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        position => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            frm.set_value('latitude', lat);
            frm.set_value('longitude', lon);
            frm.set_value('gps_location', `${lat}, ${lon}`);
            frm.set_value('check_in_time', frappe.datetime.now_datetime());
            frm.set_value('gps_status', 'Browser location fetched');

            updateMapHTML(frm, lat, lon);
        },
        error => {
            frappe.msgprint("Location permission denied. Enable GPS to continue.");
            frm.set_value('gps_status', 'Location denied');
        }
    );
}

// 📷 Open native camera only
function openNativeCameraOnly(frm) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.style.display = 'none';
    document.body.appendChild(input);

    input.onchange = () => {
        const file = input.files[0];
        if (!file) return;

        if (!['image/jpeg', 'image/png'].includes(file.type)) {
            frappe.msgprint("Only JPG or PNG files are allowed.");
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            frappe.msgprint("Image too large. Max 10MB allowed.");
            return;
        }

        if (!frm.docname || frm.is_new()) {
            frm.save().then(() => {
                uploadImageToFrappe(file, frm);
                extractExifGPS(file, frm);
            });
        } else {
            uploadImageToFrappe(file, frm);
            extractExifGPS(file, frm);
        }
    };

    input.click();
    setTimeout(() => document.body.removeChild(input), 5000);
}

// ⬆️ Upload image to Frappe
function uploadImageToFrappe(file, frm) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doctype', frm.doctype);
    formData.append('docname', frm.docname);
    formData.append('fieldname', 'upload_selfie');
    formData.append('is_private', 1);

    fetch('/api/method/upload_file', {
        method: 'POST',
        headers: {
            'X-Frappe-CSRF-Token': frappe.csrf_token
        },
        body: formData
    })
    .then(res => res.json())
    .then(r => {
        if (r.message?.file_url) {
            frm.set_value('upload_selfie', r.message.file_url);

            frm.save().then(() => {
                tryAutoSubmit(frm);
            });
        } else {
            frappe.msgprint("❌ Upload failed: " + JSON.stringify(r));
        }
    })
    .catch(err => {
        console.error("Upload error:", err);
        frappe.msgprint("❌ Upload error. Check console.");
    });
}

// 🛰️ Extract GPS from EXIF
function extractExifGPS(file, frm) {
    EXIF.getData(file, function () {
        const lat = EXIF.getTag(this, 'GPSLatitude');
        const lon = EXIF.getTag(this, 'GPSLongitude');
        const latRef = EXIF.getTag(this, 'GPSLatitudeRef');
        const lonRef = EXIF.getTag(this, 'GPSLongitudeRef');

        if (lat && lon && latRef && lonRef) {
            const latitude = convertDMSToDD(lat, latRef);
            const longitude = convertDMSToDD(lon, lonRef);

            frm.set_value('latitude', latitude);
            frm.set_value('longitude', longitude);
            frm.set_value('gps_location', `${latitude}, ${longitude}`);
            frm.set_value('gps_status', 'Photo metadata');

            updateMapHTML(frm, latitude, longitude);
        } else {
            console.log("No GPS metadata in photo. Using browser GPS...");
            requestLocationPermission(frm);
        }
    });
}

// 📌 Convert EXIF DMS to decimal
function convertDMSToDD(dms, ref) {
    const degrees = dms[0].numerator / dms[0].denominator;
    const minutes = dms[1].numerator / dms[1].denominator;
    const seconds = dms[2].numerator / dms[2].denominator;

    let dd = degrees + minutes / 60 + seconds / 3600;
    if (ref === 'S' || ref === 'W') {
        dd = -dd;
    }

    return dd;
}

// 🌍 Render embedded Google Map
function updateMapHTML(frm, lat, lon) {
    const map_url = `https://maps.google.com/maps?q=${lat},${lon}&hl=en&z=16&output=embed`;
    const html = `
        <div style="height:300px;border-radius:8px;overflow:hidden;">
            <iframe width="100%" height="100%" frameborder="0" src="${map_url}" style="border:0" allowfullscreen></iframe>
        </div>
    `;
    if (frm.fields_dict.map_html) {
        frm.fields_dict.map_html.$wrapper.html(html);
    }
}

// 🚀 Auto-submit once everything is ready
function tryAutoSubmit(frm) {
    if (
        frm.doc.upload_selfie &&
        frm.doc.latitude &&
        frm.doc.longitude &&
        frm.doc.employee &&
        frm.doc.check_in_time
    ) {
        frm.submit()
            .then(() => {
                frappe.msgprint("✅ Auto-submitted successfully!");
            })
            .catch(err => {
                console.error("Submit error:", err);
                frappe.msgprint("⚠️ Auto-submit failed. Please submit manually.");
            });
    }
}
