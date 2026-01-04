document.addEventListener("DOMContentLoaded", function () {
    const observer = new MutationObserver(() => {
        const spinner = document.querySelector('.page-loading .spinner');
        if (spinner) {
            spinner.style.backgroundImage = 'url("/files/WhatsApp_Image_2024-09-18_at_18.08.40__2_-removebg-preview.png")';
            spinner.style.backgroundSize = '120px 120px';
            spinner.style.backgroundRepeat = 'no-repeat';
            spinner.style.backgroundPosition = 'center';
            spinner.innerHTML = ''; // remove existing SVG animation

            observer.disconnect(); // stop watching once applied
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
});
