frappe.after_ajax(() => {
    const roles = frappe.boot.user.roles || [];
    const restricted_roles = ["Guard", "Supervisor", "Field Officer"];
    const should_hide = roles.some(role => restricted_roles.includes(role));

    if (should_hide) {
        setTimeout(() => {
            const searchBar = document.querySelector('.search-bar, .awesomplete, .navbar .form-control');
            if (searchBar) {
                searchBar.style.display = "none";
            }

            // Block Ctrl+G or Cmd+G shortcut
            document.addEventListener("keydown", function (e) {
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "g") {
                    e.preventDefault();
                }
            });
        }, 1000);
    }
});
