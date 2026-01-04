function hide_ui_for_roles() {
    const restricted_roles = ["Guard", "Supervisor", "Field Officer"];
    const exclude_roles = ["Administrator", "Admin"];

    // If user has any excluded role, skip
    if (exclude_roles.some(role => frappe.user.has_role(role))) {
        return;
    }

    // Apply restrictions if user has restricted roles
    if (restricted_roles.some(role => frappe.user.has_role(role))) {
        const style = document.createElement("style");
        style.innerHTML = `
            /* Hide left sidebar */
            .layout-side-section {
                display: none !important;
            }
            .layout-main-section {
                margin-left: 0 !important;
            }

            /* Hide global search button (the search bar in top navbar) */
            .navbar .navbar-search, 
            .navbar .navbar-search-button, 
            .navbar .search-bar {
                display: none !important;
            }
        `;
        document.head.appendChild(style);
    }
}

// Ensure it works in Frappe 14+ (frappe.ready) and older versions (jQuery ready)
if (frappe.ready) {
    frappe.ready(() => hide_ui_for_roles());
} else {
    $(document).ready(() => hide_ui_for_roles());
}
// sdsad