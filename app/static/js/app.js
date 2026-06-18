/**
 * Contract Manager — Minimal frontend JS.
 * Most interactions use form POST with server-side rendering.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Auto-dismiss alerts after 4 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.3s";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 300);
        }, 4000);
    });
});
