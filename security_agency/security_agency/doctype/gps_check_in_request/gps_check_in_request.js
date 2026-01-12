// Copyright (c) 2025, Anurag Sahu and contributors
// For license information, please see license.txt

frappe.require('/assets/security_agency/js/exif.js');
frappe.ui.form.on('GPS Check-in Request', {
    refresh: function (frm) {
        if (frm.doc.upload_selfie) {
            frm.fields_dict.selfie_preview.$wrapper.html(`
                <img src="${frm.doc.upload_selfie}" style="max-width: 200px;">
            `);
        }
    },
    upload_selfie: function (frm) {
        if (frm.doc.upload_selfie) {
            frm.fields_dict.selfie_preview.$wrapper.html(`
                <img src="${frm.doc.upload_selfie}" style="max-width: 200px;">
            `);
        }
    }
});

frappe.ui.form.on("GPS Check-in Request", {
    onload(frm) {
        if (!frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user },
                    fields: ["name"]
                },
                callback(response) {
                    if (response.message?.length > 0) {
                        frm.set_value("employee", response.message[0].name);
                    }
                }
            });
        }

        if (frappe.session.user !== 'Administrator') {
            frm.set_df_property('employee', 'read_only', 1);
            frm.set_df_property('repoting_to', 'read_only', 1);
        }

        if (frm.doc.docstatus === 0) {
            requestLocationPermission(frm);
        }
    },

    validate(frm) {
        if (frm.doc.docstatus === 1) {
            frappe.throw("This document is already submitted and cannot be modified.");
        }
    },

    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.disable_save();
            frm.set_df_property("selfie", "read_only", 1);
            frm.set_df_property("site", "read_only", 1);
        } else {
            frm.fields_dict.selfie.$wrapper.find('.btn-attach').hide();

            if (!frm.fields_dict.selfie.$wrapper.find('.capture-photo-btn').length) {
                frm.fields_dict.selfie.$wrapper.append(`
                    <button class="btn btn-primary btn-sm capture-photo-btn" style="margin-top: 5px;">
                        Capture Photo from Camera
                    </button>
                    <input type="file" id="file-upload" accept="image/*" style="display:none" />
                    <button class="btn btn-secondary btn-sm upload-photo-btn" style="margin-top: 5px; margin-left: 5px;">
                        Upload Image
                    </button>
                `);

                frm.fields_dict.selfie.$wrapper.find('.capture-photo-btn').on('click', () => {
                    openNativeCameraOnly(frm);
                });

                frm.fields_dict.selfie.$wrapper.find('.upload-photo-btn').on('click', () => {
                    document.getElementById('file-upload').click();
                });

                document.getElementById('file-upload').addEventListener('change', function() {
                    const file = this.files[0];
                    if (file) {
                        handleImageUpload(file, frm);
                    }
                });
            }
        }

        if (frm.doc.latitude && frm.doc.longitude) {
            updateMapHTML(frm, frm.doc.latitude, frm.doc.longitude);
        }
    },

    employee(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, 'reports_to')
                .then(r => {
                    frm.set_value('repoting_to', r.message?.reports_to || '');
                });
        }
    }
});

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
        () => {
            frappe.msgprint("Location permission denied. Enable GPS to continue.");
            frm.set_value('gps_status', 'Location denied');
        }
    );
}

function openNativeCameraOnly(frm) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.style.display = 'none';
    document.body.appendChild(input);

    input.onchange = () => {
        const file = input.files[0];
        if (file) handleImageUpload(file, frm);
    };

    input.click();
    setTimeout(() => document.body.removeChild(input), 5000);
}

function handleImageUpload(file, frm) {
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
}

function uploadImageToFrappe(file, frm) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doctype', frm.doctype);
    formData.append('docname', frm.docname);
    formData.append('fieldname', 'selfie');
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
            frm.set_value('selfie', r.message.file_url);
            frm.save();
        } else {
            frappe.msgprint("Failed to upload image: " + JSON.stringify(r));
        }
    })
    .catch(err => {
        console.error("Upload error:", err);
        frappe.msgprint("Upload failed. Check console for details.");
    });
}

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
            requestLocationPermission(frm);
        }
    });
}

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
frappe.ui.form.on('GPS Check-in Request', {
    refresh: function(frm) {
        // show our field-level button only if document is Draft
        frm.toggle_display('submit', !frm.is_new() && frm.doc.docstatus === 0);
    },

    // this name must exactly match the fieldname of the Button in the DocType
    submit: function(frm) {
        frappe.confirm(
            __('Are you sure you want to submit this Check-in?'),
            function() {
                frm.save('Submit');   // ✅ submit the doc
            }
        );
    }
});

// frappe.ui.form.on('GPS Check-in Request', {
//     refresh(frm) {
//         // Hide default attach field
//         frm.set_df_property('upload_selfie', 'hidden', 1);

//         // Inject camera UI
//         frm.fields_dict.camera_capture.$wrapper.html(`
//             <div style="text-align:center">
//                 <video id="gps_video" autoplay playsinline
//                     style="width:100%; max-height:300px; border-radius:8px;"></video>

//                 <canvas id="gps_canvas" style="display:none;"></canvas>

//                 <br><br>
//                 <button class="btn btn-primary" id="gps_capture">
//                     📷 Capture Selfie
//                 </button>
//             </div>
//         `);

//         start_camera();
//         bind_capture(frm);
//     }
// });

// /* ---------------- CAMERA START ---------------- */

// function start_camera() {
//     if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
//         frappe.msgprint("Camera not supported on this device");
//         return;
//     }

//     navigator.mediaDevices.getUserMedia({
//         video: { facingMode: "user" },
//         audio: false
//     }).then(stream => {
//         const video = document.getElementById("gps_video");
//         video.srcObject = stream;
//         video.play();
//     }).catch(err => {
//         frappe.msgprint("Camera permission denied");
//     });
// }

// /* ---------------- CAPTURE HANDLER ---------------- */

// function bind_capture(frm) {
//     const btn = document.getElementById("gps_capture");

//     btn.onclick = () => {
//         const video = document.getElementById("gps_video");
//         const canvas = document.getElementById("gps_canvas");

//         // ⚠️ Camera not ready yet
//         if (!video.videoWidth || !video.videoHeight) {
//             frappe.msgprint("Camera is not ready yet. Please wait.");
//             return;
//         }

//         canvas.width = video.videoWidth;
//         canvas.height = video.videoHeight;

//         const ctx = canvas.getContext("2d");
//         ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

//         // ✅ Compress image slightly (mobile friendly)
//         const imageData = canvas.toDataURL("image/jpeg", 0.85);

//         upload_to_frappe(imageData, frm);
//     };
// }

// /* ---------------- UPLOAD TO FRAPPE ---------------- */

// function upload_to_frappe(imageData, frm) {
//     // ❌ Empty or failed capture
//     if (!imageData || imageData === "data:,") {
//         frappe.msgprint("Selfie capture failed. Please try again.");
//         return;
//     }

//     // 🔥 IMPORTANT: strip base64 header
//     const base64 = imageData.split(",")[1];

//     frappe.call({
//         method: "frappe.client.attach_file",
//         args: {
//             doctype: frm.doctype,
//             docname: frm.docname,
//             fieldname: "upload_selfie",
//             filedata: base64,       // ⚠️ base64 ONLY
//             filename: "selfie.jpg"
//         },
//         callback: function () {
//             frappe.show_alert({
//                 message: "Selfie captured successfully",
//                 indicator: "green"
//             });
//         }
//     });
// }

