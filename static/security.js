/* ============================================================
   AIR CURSOR ULTIMATE SECURITY & ANTI-INSPECT ENGINE
============================================================ */

// ૧. Right-Click બંધ કરવું
document.addEventListener('contextmenu', function (e) {
    e.preventDefault();
    showWarning("Right Click is Prohibited!");
});

// ૨. F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C, Ctrl+U બ્લોક કરવું
document.onkeydown = function (e) {
    if (e.keyCode == 123) { // F12
        e.preventDefault();
        showWarning("Developer Tools Access Denied!");
        return false;
    }
    if (e.ctrlKey && e.shiftKey && (e.keyCode == 'I'.charCodeAt(0) || e.keyCode == 'J'.charCodeAt(0) || e.keyCode == 'C'.charCodeAt(0))) {
        e.preventDefault();
        showWarning("Inspect Element is Strictly Prohibited!");
        return false;
    }
    if (e.ctrlKey && e.keyCode == 'U'.charCodeAt(0)) { // Ctrl + U
        e.preventDefault();
        showWarning("Source Code Viewing is Disabled!");
        return false;
    }
};

// ૩. DevTools Detection (જો કોઈ સાઇડ મેનૂમાંથી Inspect ખોલે તો સ્ક્રીન ફ્રીઝ કરવી)
let devtoolsOpen = false;
const threshold = 160;
setInterval(function() {
    if (window.outerWidth - window.innerWidth > threshold || window.outerHeight - window.innerHeight > threshold) {
        if (!devtoolsOpen) {
            devtoolsOpen = true;
            document.body.innerHTML = `
                <div style="height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;background:#0d0d0f;color:#ff3366;font-family:sans-serif;text-align:center;padding:20px;">
                    <h1 style="font-size:2.5rem;margin-bottom:10px;">⚠️ SECURITY ALERT</h1>
                    <h2 style="color:#ffffff;">Developer Inspection is Strictly Forbidden!</h2>
                    <p style="color:#aaa;max-width:500px;margin-top:10px;">Tampering with the DOM tree or debugging runtime components is prohibited on the Air Cursor enterprise network. Close developer tools and reload.</p>
                </div>
            `;
        }
    }
}, 500);

// ૪. ક્લાયન્ટ-સાઇડ હાર્ડવેર વેરિફિકેશન (Smart Boards, Tablets, Touch Devices બ્લોક)
(function enforceHardwareRestrictions() {
    const isTouchScreen = navigator.maxTouchPoints > 1;
    const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Macintosh|MacIntel/i.test(navigator.userAgent);
    
    // Windows PC સિવાયની કોઈ પણ વસ્તુ
    const isWindows = navigator.platform.indexOf('Win') > -1 || navigator.userAgent.indexOf('Windows') > -1;

    if (!isWindows || (isMobileUA && !isWindows)) {
        window.location.href = "/error/403";
    }
})();

function showWarning(msg) {
    const existing = document.getElementById('security-toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.id = 'security-toast';
    toast.innerText = '🛡️ ' + msg;
    toast.style.position = 'fixed';
    toast.style.bottom = '30px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.background = 'rgba(255, 45, 85, 0.95)';
    toast.style.color = '#fff';
    toast.style.padding = '12px 26px';
    toast.style.borderRadius = '30px';
    toast.style.fontWeight = 'bold';
    toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
    toast.style.zIndex = '999999';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}
