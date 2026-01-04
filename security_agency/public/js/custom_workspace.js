// ✅ Compatible with both Web and Android WebView (no dependencies)
(function waitForWorkspace() {
    const ready = document.querySelectorAll(".workspace .shortcut");
    if (ready.length > 0) {
        console.log("✅ Custom JS: UI enhancements active");

        // Example: Add tooltip dynamically
        ready.forEach(el => {
            const label = el.textContent.trim();
            el.setAttribute("title", "Open: " + label);
        });

        // Example: Highlight active shortcut
        const currentPath = window.location.pathname;
        ready.forEach(el => {
            const link = el.getAttribute("href");
            if (link && currentPath.includes(link)) {
                el.style.border = "2px solid #007bff";
            }
        });

    } else {
        setTimeout(waitForWorkspace, 500); // Retry until workspace loads
    }
})();
