frappe.ready(() => {
    const observer = new MutationObserver(() => {
        const logo = document.querySelector(".navbar-home");
        if (logo && logo.getAttribute("href") !== "/app/operations-module") {
            logo.setAttribute("href", "/app/operations-module");

            logo.addEventListener("click", function (e) {
                e.preventDefault();
                window.location.href = "/app/operations-module";
            });
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
});
