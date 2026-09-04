/**
 * AIR CURSOR - UNIFIED MASTER FRONTEND SCRIPT
 * Seamlessly integrates:
 * 1. Page Loader & State
 * 2. Universal Gold-Obsidian Modals (No Native Browser Popups)
 * 3. Native Web Audio Synthesizer
 * 4. Day / Night Animated Theme Switcher
 * 5. Interactive Canvas & Particle Logo System
 * 6. Navbar Auto-Hide & Scroll Tracker
 * 7. Strict Form Validation (Bans +, -, *, / & special symbols)
 * 8. Device Avatar Upload & Instant DB Reset
 */

// =========================================================
// 💥 ૧. પેજ લોડર હેન્ડલર 💥
// =========================================================
function dismissLoader() {
    const loaderWrapper = document.getElementById('loader-wrapper');
    const mainContent = document.getElementById('main-content');

    if (loaderWrapper) {
        loaderWrapper.style.transition = 'opacity 0.4s ease, visibility 0.4s ease';
        loaderWrapper.style.opacity = '0';
        loaderWrapper.style.visibility = 'hidden';
        loaderWrapper.style.pointerEvents = 'none';
        setTimeout(() => {
            loaderWrapper.style.display = 'none';
        }, 450);
    }
    if (mainContent) {
        mainContent.style.transition = 'opacity 0.4s ease';
        mainContent.style.opacity = '1';
        mainContent.style.visibility = 'visible';
    }
}

if (document.readyState === 'complete') {
    setTimeout(dismissLoader, 200);
} else {
    window.addEventListener('load', () => setTimeout(dismissLoader, 300));
}
setTimeout(dismissLoader, 1500);

// =========================================================
// 💥 ૨. NATIVE WEB AUDIO SYNTHESIZER (NO EXTERNAL MP3) 💥
// =========================================================
const AudioEngine = {
    ctx: null,
    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
    },
    playClick() {
        try {
            this.init();
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(600, now);
            osc.frequency.exponentialRampToValueAtTime(850, now + 0.1);
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.linearRampToValueAtTime(0.01, now + 0.1);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 0.1);
        } catch (e) {}
    },
    playWarning() {
        try {
            this.init();
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(260, now);
            osc.frequency.linearRampToValueAtTime(140, now + 0.25);
            gain.gain.setValueAtTime(0.3, now);
            gain.gain.linearRampToValueAtTime(0.01, now + 0.25);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 0.25);
        } catch (e) {}
    },
    playSuccess() {
        try {
            this.init();
            const notes = [523.25, 659.25, 783.99]; // C Major Chord Chime
            notes.forEach((freq, i) => {
                const now = this.ctx.currentTime + (i * 0.08);
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(freq, now);
                gain.gain.setValueAtTime(0.2, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
                osc.connect(gain);
                gain.connect(this.ctx.destination);
                osc.start(now);
                osc.stop(now + 0.3);
            });
        } catch (e) {}
    }
};

// =========================================================
// 💥 ૩. UNIVERSAL LUXURY MODAL ENGINE (ZERO BROWSER ALERTS) 💥
// =========================================================
function ensureUniversalModalExists() {
    if (!document.getElementById('globalAppModal')) {
        const modalHtml = `
            <div id="globalAppModal" style="display: none; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); justify-content: center; align-items: center; z-index: 9999999; padding: 20px;">
                <div style="background: #16171d; border: 1px solid rgba(197, 168, 128, 0.35); border-radius: 28px; padding: 35px 30px; width: 100%; max-width: 440px; text-align: center; color: #fff; box-shadow: 0 25px 60px rgba(0,0,0,0.8), 0 0 30px rgba(197,168,128,0.15); animation: popModalAnim 0.25s ease-out;">
                    <span id="globalModalEmoji" style="font-size: 3.5rem; margin-bottom: 12px; display: block; line-height: 1;">⚠️</span>
                    <div id="globalModalTitle" style="color: #C5A880; font-size: 1.35rem; font-weight: 800; margin-bottom: 10px; letter-spacing: -0.3px;">Notification</div>
                    <div id="globalModalMsg" style="color: rgba(230, 228, 224, 0.78); font-size: 0.95rem; line-height: 1.6; margin-bottom: 25px; white-space: pre-line;"></div>
                    <div style="display: flex; justify-content: center; gap: 12px;">
                        <button id="globalModalCancelBtn" style="display: none; background: #252830; color: #E6E4E0; border: 1px solid rgba(255,255,255,0.15); padding: 10px 24px; border-radius: 99px; font-weight: 600; cursor: pointer; font-size: 0.88rem;">Cancel</button>
                        <button id="globalModalConfirmBtn" style="background: linear-gradient(135deg, #C5A880 0%, #E6E4E0 100%); color: #0c0d11; border: none; padding: 10px 28px; border-radius: 99px; font-weight: 800; font-size: 0.9rem; cursor: pointer;">Understood</button>
                    </div>
                </div>
            </div>
            <style>
                @keyframes popModalAnim {
                    from { opacity: 0; transform: scale(0.92); }
                    to { opacity: 1; transform: scale(1); }
                }
            </style>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
}

let globalModalCallback = null;

function showCustomModal(emoji, title, message, btnText = 'Understood', showCancel = false, onConfirm = null) {
    ensureUniversalModalExists();
    document.getElementById('globalModalEmoji').innerText = emoji || '🔔';
    document.getElementById('globalModalTitle').innerText = title || 'Notice';
    document.getElementById('globalModalMsg').innerHTML = message;
    document.getElementById('globalModalConfirmBtn').innerText = btnText;
    
    const cancelBtn = document.getElementById('globalModalCancelBtn');
    cancelBtn.style.display = showCancel ? 'inline-block' : 'none';
    
    globalModalCallback = onConfirm;
    document.getElementById('globalAppModal').style.display = 'flex';
}

function closeCustomModal() {
    const modal = document.getElementById('globalAppModal');
    if (modal) modal.style.display = 'none';
    globalModalCallback = null;
}

// 💥 OVERRIDE BROWSER ALERTS GLOBALLY 💥
window.alert = function(msg) {
    AudioEngine.playWarning();
    showCustomModal('🔔', 'Notification', msg, 'OK', false, null);
};

document.addEventListener('click', function(e) {
    if (e.target && e.target.id === 'globalModalConfirmBtn') {
        if (globalModalCallback) globalModalCallback();
        closeCustomModal();
    }
    if (e.target && e.target.id === 'globalModalCancelBtn') {
        closeCustomModal();
    }
});

// =========================================================
// 💥 ૪. ડાર્ક / લાઈટ થીમ મેનેજર & ANIMATED SWITCH 💥
// =========================================================
(function () {
    "use strict";
    let savedTheme = localStorage.getItem("air_theme") || localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    if (savedTheme === "light") {
        document.body.classList.add("light-mode");
    }

    window.toggleTheme = function() {
        AudioEngine.playClick();
        const isCurrentlyLight = document.body.classList.contains("light-mode") || document.documentElement.getAttribute("data-theme") === "light";
        const newTheme = isCurrentlyLight ? "dark" : "light";

        document.documentElement.setAttribute("data-theme", newTheme);
        document.body.classList.toggle("light-mode", newTheme === "light");
        localStorage.setItem("air_theme", newTheme);
        localStorage.setItem("theme", newTheme);

        const oldThemeToggleBtn = document.getElementById("themeToggle");
        if (oldThemeToggleBtn) {
            oldThemeToggleBtn.classList.toggle("is-night", newTheme === "dark");
        }
    };

    document.addEventListener("DOMContentLoaded", () => {
        const toggleElements = document.querySelectorAll('.day-night-toggle, .theme-switch-box, #themeToggle');
        toggleElements.forEach(el => {
            el.addEventListener('click', function(e) {
                e.stopPropagation();
                window.toggleTheme();
            });
        });
    });
})();

// =========================================================
// 💥 ૫. કેનવાસ અને પાર્ટીકલ સિસ્ટમ 💥
// =========================================================
const canvas = document.getElementById("particleCanvas") || document.createElement('canvas');
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth || 800;
canvas.height = window.innerHeight || 600;

let particlesArray = [];
let logoPoints = [];
let scrollProgress = 0;

// નેવબાર ઓટો-હાઈડ અને સ્ક્રૉલ લિસનર
window.addEventListener('scroll', () => {
    let maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    if (maxScroll <= 0) maxScroll = 1200;
    scrollProgress = Math.min(1, Math.max(0, window.scrollY / maxScroll));

    const topNav = document.querySelector('.top-nav');
    if (topNav) {
        if (window.scrollY > 80) {
            topNav.classList.add('hide-nav');
        } else {
            topNav.classList.remove('hide-nav');
        }
    }
});

function createLogoPoints() {
    const w = window.innerWidth || 800;
    const h = window.innerHeight || 600;

    const tempCanvas = document.createElement('canvas');
    const tCtx = tempCanvas.getContext('2d');
    tempCanvas.width = w;
    tempCanvas.height = h;

    let cx = w / 2;
    let cy = h / 2 - 50; 
    let s = 1.7; 

    tCtx.translate(cx, cy);
    tCtx.scale(s, s);
    
    tCtx.lineWidth = 5; 
    tCtx.lineJoin = "round";
    tCtx.lineCap = "round";

    tCtx.strokeStyle = "rgba(0, 0, 255, 1)"; 
    tCtx.beginPath();
    tCtx.moveTo(0, -75);     
    tCtx.lineTo(50, 60);     
    tCtx.lineTo(0, 20);      
    tCtx.lineTo(-50, 60);    
    tCtx.closePath();
    tCtx.stroke(); 

    tCtx.fillStyle = "rgba(255, 0, 0, 1)"; 
    tCtx.beginPath();
    tCtx.moveTo(0, -35);     
    tCtx.lineTo(24, 25);     
    tCtx.lineTo(0,  5);      
    tCtx.lineTo(-24, 25);    
    tCtx.closePath();
    tCtx.fill(); 

    tCtx.fillStyle = "rgba(0, 255, 0, 1)"; 
    tCtx.font = "bold 32px system-ui, sans-serif";
    tCtx.textAlign = "center";
    
    let hiddenTextEl = document.getElementById('hidden-welcome-text');
    let welcomeText = hiddenTextEl ? hiddenTextEl.innerText : "Welcome";
    tCtx.fillText(welcomeText, 0, 160); 

    const imgData = tCtx.getImageData(0, 0, w, h);
    const data = imgData.data;
    logoPoints = [];

    for(let y = 0; y < h; y += 2) { 
        for(let x = 0; x < w; x += 2) {
            const idx = (Math.floor(y) * w + Math.floor(x)) * 4;
            const r = data[idx];
            const g = data[idx + 1];
            const alpha = data[idx + 3];

            if (alpha > 100) {
                let pColor = "cyan"; 
                if (r > 128 && g < 128) pColor = "white_cursor";
                else if (g > 128 && r < 128) pColor = "welcome";
                logoPoints.push({ x: x, y: y, colorType: pColor });
            }
        }
    }
}

class Particle {
    constructor(baseX, baseY, colorType) {
        this.baseX = baseX;
        this.baseY = baseY;
        this.colorType = colorType; 
        this.x = this.baseX;
        this.y = this.baseY;
        this.snowX = Math.random() * canvas.width;
        this.snowY = Math.random() * canvas.height;
        this.fallSpeed = Math.random() * 0.7 + 0.35; 
        this.driftSpeed = (Math.random() - 0.5) * 0.4;
        this.snowAngle = Math.random() * Math.PI * 2;
    }

    update() {
        let targetX = this.baseX;
        let targetY = this.baseY;

        if (scrollProgress > 0.05) {
            this.snowY += this.fallSpeed;
            this.snowAngle += 0.02;
            this.snowX += Math.sin(this.snowAngle) * 0.5 + this.driftSpeed;

            if (this.snowY > canvas.height + 10) {
                this.snowY = -10;
                this.snowX = Math.random() * canvas.width;
            }
            if (this.snowX < -10) this.snowX = canvas.width + 10;
            else if (this.snowX > canvas.width + 10) this.snowX = -10;

            let blend = Math.min(1, (scrollProgress - 0.05) / 0.15);
            targetX = this.baseX + (this.snowX - this.baseX) * blend;
            targetY = this.baseY + (this.snowY - this.baseY) * blend;

            this.x += (targetX - this.x) * 0.08;
            this.y += (targetY - this.y) * 0.08;
        } else {
            this.x += (this.baseX - this.x) * 0.15;
            this.y += (this.baseY - this.y) * 0.15;
        }
    }

    draw() {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        let alpha = scrollProgress > 0.05 ? 0.65 : 0.95;
        
        if (this.colorType === "white_cursor") {
            ctx.fillStyle = currentTheme === "dark" 
                ? `rgba(255, 255, 255, ${alpha})` 
                : `rgba(15, 23, 42, ${alpha})`; 
        } else {
            ctx.fillStyle = currentTheme === "dark" 
                ? `rgba(0, 242, 254, ${alpha})`   
                : `rgba(0, 102, 204, ${alpha})`;  
        }
        
        ctx.fillRect(this.x, this.y, 1.2, 1.2);
    }
}

function init() {
    canvas.width = window.innerWidth || 800;
    canvas.height = window.innerHeight || 600;
    createLogoPoints();
    particlesArray = [];
    for (let i = 0; i < logoPoints.length; i++) {
        particlesArray.push(new Particle(logoPoints[i].x, logoPoints[i].y, logoPoints[i].colorType));
    }
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < particlesArray.length; i++) {
        particlesArray[i].update();
        particlesArray[i].draw();
    }
    requestAnimationFrame(animate);
}

window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    init();
});

init();
animate();

// =========================================================
// 💥 ૬. STRICT VALIDATION (+, -, *, / BANNED) & FORM CONTROLS 💥
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
    ensureUniversalModalExists();

    const downloadForm = document.getElementById('downloadForm') || document.querySelector('form[action="/register"]');
    const rememberCheckbox = document.getElementById('remember');

    // રીમાઇન્ડર મોડલ (Are you sure?)
    const reminderModal = document.getElementById('reminderModal');
    const reminderBackBtn = document.getElementById('reminderBackBtn');
    const reminderOkBtn = document.getElementById('reminderOkBtn');

    // સેશન એક્સપાયર્ડ મોડલ
    const expiredModal = document.getElementById('expiredModal');
    const expiredOkBtn = document.getElementById('expiredOkBtn');

    let bypassReminder = false;

    if (downloadForm) {
        downloadForm.addEventListener('submit', (e) => {
            const nameInput = downloadForm.querySelector('input[name="name"]');
            const emailInput = downloadForm.querySelector('input[name="email"]');
            
            const nameValue = nameInput ? nameInput.value.trim() : '';
            const emailValue = emailInput ? emailInput.value.trim() : '';

            // ❌ Prohibited characters: +, -, *, /, ~, `, !, #, $, %, ^, &, (, ), =, _, etc.
            const forbiddenSymbols = /[+\-*\/~`!#$%^&()=_{}\[\]:;"'<>,?|\\]/;

            // ૧. બંને ખાલી હોય ત્યારે
            if (!nameValue && !emailValue) {
                e.preventDefault();
                AudioEngine.playWarning();
                showCustomModal("📝", "Action Required!", "Please fill out both name and email fields!");
                return;
            }

            // ૨. નામ ખાલી હોય ત્યારે
            if (!nameValue) {
                e.preventDefault();
                AudioEngine.playWarning();
                showCustomModal("👤", "Action Required!", "Oops! You forgot to enter your Full Name.");
                return;
            }

            // ૩. 💥 ચિહ્નો (+, -, *, /) ચેક કરવા 💥
            if (forbiddenSymbols.test(nameValue) || forbiddenSymbols.test(emailValue)) {
                e.preventDefault();
                AudioEngine.playWarning();
                showCustomModal(
                    "⚠️",
                    "Invalid Characters Detected!",
                    "Symbols like <b>+ - * /</b> or special characters are strictly prohibited!<br><br>Please use only <b>Letters</b>, <b>Numbers</b>, <b>@</b>, and <b>.</b> (dot)."
                );
                return;
            }

            // ૪. નામ ૩ અક્ષરથી ઓછું હોય ત્યારે
            if (nameValue.length < 3) {
                e.preventDefault();
                AudioEngine.playWarning();
                showCustomModal("⚠️", "Action Required!", "Name must contain at least 3 characters or letters!");
                return;
            }

            // ૫. નામમાં ફક્ત લેટર્સ, નંબર્સ અને સ્પેસ
            const nameRegex = /^[a-zA-Z0-9\s]+$/;
            if (!nameRegex.test(nameValue)) {
                e.preventDefault();
                AudioEngine.playWarning();
                showCustomModal("⚠️", "Invalid Name Format", "Full Name can only contain letters, numbers, and spaces.");
                return;
            }

            // ૬. ઇમેલ ખાલી હોય ત્યારે
            if (!emailValue) {
                e.preventDefault();
                AudioEngine.playWarning();
                showCustomModal("📧", "Action Required!", "Oops! You forgot to enter your Work Email Address.");
                return;
            }

            // ૭. 💥 કડક ઇમેલ વેરિફિકેશન (NO +1 ALIASES, STRICT EXTENSION) 💥
            const strictEmailRegex = /^[a-zA-Z0-9.]+@[a-zA-Z0-9.]+\.[a-zA-Z]{2,}$/;
            if (!strictEmailRegex.test(emailValue) || emailValue.includes('..') || emailValue.startsWith('.') || emailValue.split('@')[0].endsWith('.')) {
                e.preventDefault();
                AudioEngine.playWarning();
                showCustomModal("💥", "Invalid Email Address!", "Please enter a valid email format (e.g. <b>user@gmail.com</b>).<br>Aliases like <b>+1</b> or duplicate dots are strictly rejected.");
                return;
            }

            // ૮. Remember Me ચેક ના હોય તો Warning પોપઅપ
            if (rememberCheckbox && !rememberCheckbox.checked && !bypassReminder) {
                e.preventDefault();
                if (reminderModal) {
                    reminderModal.style.display = 'flex';
                } else {
                    showCustomModal(
                        "🔒",
                        "Remember Me Unchecked",
                        "You did not check 'Remember Me'. Your session will automatically expire after browser closure.<br><br>Do you wish to proceed?",
                        "Proceed Anyway",
                        true,
                        () => {
                            bypassReminder = true;
                            downloadForm.submit();
                        }
                    );
                }
                return;
            }

            AudioEngine.playSuccess();
        });
    }

    // Remember Me Modals controls
    if (reminderBackBtn) {
        reminderBackBtn.addEventListener('click', () => {
            if (reminderModal) reminderModal.style.display = 'none';
            if (rememberCheckbox) rememberCheckbox.focus();
        });
    }

    if (reminderOkBtn) {
        reminderOkBtn.addEventListener('click', () => {
            bypassReminder = true;
            if (reminderModal) reminderModal.style.display = 'none';
            if (downloadForm) downloadForm.submit();
        });
    }

    // URL માં action=download_click હોય ત્યારે સેશન એક્સપાયર્ડ પોપઅપ
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('action') === 'download_click' && expiredModal) {
        expiredModal.style.display = 'flex';
    }

    if (expiredOkBtn) {
        expiredOkBtn.addEventListener('click', () => {
            if (expiredModal) expiredModal.style.display = 'none';
            window.history.replaceState({}, document.title, window.location.pathname);
            const downloadSec = document.getElementById('download');
            if (downloadSec) downloadSec.scrollIntoView({ behavior: 'smooth' });
        });
    }
});

// =========================================================
// 💥 ૭. DEVICE AVATAR UPLOAD & REMOVE (ZERO BROWSER ALERTS) 💥
// =========================================================
const DEFAULT_AVATAR_IMG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0%25' stop-color='%234ea5ff'/><stop offset='50%25' stop-color='%232a85ff'/><stop offset='100%25' stop-color='%231868db'/></linearGradient><linearGradient id='a' x1='0' y1='0' x2='0' y2='1'><stop offset='0%25' stop-color='%23ffffff'/><stop offset='100%25' stop-color='%23e2edfc'/></linearGradient></defs><circle cx='50' cy='50' r='50' fill='url(%23g)'/><circle cx='50' cy='37' r='15' fill='url(%23a)'/><path d='M 23.5 80 C 23.5 63 35 56 50 56 C 65 56 76.5 63 76.5 80 Z' fill='url(%23a)'/></svg>";

function uploadAvatarFromDevice(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(evt) {
            const dataUrl = evt.target.result;
            const preview = document.getElementById('previewAvatar');
            const dock = document.getElementById('dockAvatarImg');
            if (preview) preview.src = dataUrl;
            if (dock) dock.src = dataUrl;
            
            // MongoDB Database માં સેવ કરવું
            fetch('/api/admin/avatar/upload', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ avatar_url: dataUrl })
            }).then(() => {
                AudioEngine.playSuccess();
            });
        };
        reader.readAsDataURL(file);
    }
}

function removeAdminAvatar() {
    // 💥 NO BROWSER CONFIRM - USES LUXURY MODAL! 💥
    showCustomModal(
        '🗑️',
        'Reset Avatar Photo',
        'Are you sure you want to remove your custom uploaded photo and reset back to the default blue avatar?',
        'Reset Avatar',
        true,
        () => {
            fetch('/api/admin/avatar/remove', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                const preview = document.getElementById('previewAvatar');
                const dock = document.getElementById('dockAvatarImg');
                const fileInput = document.getElementById('avatarFileInput');

                if (preview) preview.src = data.default_avatar || DEFAULT_AVATAR_IMG;
                if (dock) dock.src = data.default_avatar || DEFAULT_AVATAR_IMG;
                if (fileInput) fileInput.value = '';

                AudioEngine.playSuccess();
                showCustomModal('✅', 'Reset Completed', 'Profile picture removed and reset to default successfully.', 'OK', false, null);
            });
        }
    );
}

// Download Modal Helper
function openDownloadModal() {
    AudioEngine.playClick();
    const modal = document.getElementById('downloadModal') || document.getElementById('leadModal');
    if (modal) modal.style.display = 'flex';
}

function closeDownloadModal() {
    AudioEngine.playClick();
    const modal = document.getElementById('downloadModal') || document.getElementById('leadModal');
    if (modal) modal.style.display = 'none';
}
