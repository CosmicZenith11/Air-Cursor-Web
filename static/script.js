// ૧. પેજ લોડર હેન્ડલર
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

// ૨. ડાર્ક / લાઈટ થીમ મેનેજર
(function () {
  "use strict";
  let savedTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);

  const themeToggleBtn = document.getElementById("themeToggle");
  if (themeToggleBtn) {
    if (savedTheme === "dark") {
      themeToggleBtn.classList.add("is-night");
    } else {
      themeToggleBtn.classList.remove("is-night");
    }
    themeToggleBtn.addEventListener("click", function () {
      let isNightNow = themeToggleBtn.classList.contains("is-night");
      let newTheme = isNightNow ? "light" : "dark";
      themeToggleBtn.classList.toggle("is-night", !isNightNow);
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
    });
  }
})();

// ૩. કેનવાસ અને પાર્ટીકલ સિસ્ટમ
const canvas = document.getElementById("particleCanvas") || document.createElement('canvas');
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth || 800;
canvas.height = window.innerHeight || 600;

let particlesArray = [];
let logoPoints = [];
let scrollProgress = 0;

// ૪. નેવબાર ઓટો-હાઈડ અને સ્ક્રૉલ લિસનર
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

// 💥 ૫. તમામ કસ્ટમ પોપઅપ્સ (Validation, Remember-Me Warning, Session Expired) 💥
document.addEventListener('DOMContentLoaded', () => {
    const downloadForm = document.getElementById('downloadForm');
    const rememberCheckbox = document.getElementById('remember');

    // કસ્ટમ વેલિડેશન પોપઅપ
    const customPopup = document.getElementById('custom-popup');
    const popupIcon = document.getElementById('popup-icon');
    const popupTitle = document.getElementById('popup-title');
    const popupMessage = document.getElementById('popup-message');
    const popupCloseBtn = document.getElementById('popup-close-btn');

    // રીમાઇન્ડર મોડલ (Are you sure?)
    const reminderModal = document.getElementById('reminderModal');
    const reminderBackBtn = document.getElementById('reminderBackBtn');
    const reminderOkBtn = document.getElementById('reminderOkBtn');

    // સેશન એક્સપાયર્ડ મોડલ
    const expiredModal = document.getElementById('expiredModal');
    const expiredOkBtn = document.getElementById('expiredOkBtn');

    let bypassReminder = false;

    function showPopup(icon, title, message) {
        if (customPopup) {
            popupIcon.innerHTML = icon;
            popupTitle.innerText = title;
            popupMessage.innerText = message;
            customPopup.style.display = 'flex';
            customPopup.classList.add('active');
        }
    }

    if (popupCloseBtn) {
        popupCloseBtn.addEventListener('click', () => {
            if (customPopup) {
                customPopup.style.display = 'none';
                customPopup.classList.remove('active');
            }
        });
    }

    // ફોર્મ સબમિટ વેલિડેશન
    if (downloadForm) {
        downloadForm.addEventListener('submit', (e) => {
            const nameInput = downloadForm.querySelector('input[name="name"]');
            const emailInput = downloadForm.querySelector('input[name="email"]');
            
            const nameValue = nameInput ? nameInput.value.trim() : '';
            const emailValue = emailInput ? emailInput.value.trim() : '';
            const emailRegex = /^[^\s@]+@[^\s@]+\.(com|in|org|net|edu|gov|co|io)$/i;

            // ૧. બંને ખાલી હોય ત્યારે
            if (!nameValue && !emailValue) {
                e.preventDefault();
                showPopup("📝", "Action Required!", "Please fill out both name and email fields!");
                return;
            }
            // ૨. નામ ખાલી હોય ત્યારે
            if (!nameValue) {
                e.preventDefault();
                showPopup("👤", "Action Required!", "Oops! You forgot to enter your Your Name.");
                return;
            }
            // ૩. નામ ૩ અક્ષરથી ઓછું હોય ત્યારે
            if (nameValue.length < 3) {
                e.preventDefault();
                showPopup("⚠️", "Action Required!", "Name must contain at least 3 characters or letters!");
                return;
            }
            // ૪. ઇમેલ ખાલી હોય ત્યારે
            if (!emailValue) {
                e.preventDefault();
                showPopup("📧", "Action Required!", "Oops! You forgot to enter your Work Email Address.");
                return;
            }
            // ૫. ઇમેલ ફોર્મેટ ખોટું હોય ત્યારે
            if (!emailRegex.test(emailValue)) {
                e.preventDefault();
                showPopup("💥", "Action Required!", "Please enter a valid email address with a proper extension (like .com, .in, etc.)!");
                return;
            }

            // ૬. Remember Me ચેક ના હોય તો Warning પોપઅપ
            if (rememberCheckbox && !rememberCheckbox.checked && !bypassReminder) {
                e.preventDefault();
                if (reminderModal) reminderModal.style.display = 'flex';
            }
        });
    }

    // Remember Me Back બટન
    if (reminderBackBtn) {
        reminderBackBtn.addEventListener('click', () => {
            if (reminderModal) reminderModal.style.display = 'none';
            if (rememberCheckbox) rememberCheckbox.focus();
        });
    }

    // Remember Me Proceed બટન
    if (reminderOkBtn) {
        reminderOkBtn.addEventListener('click', () => {
            bypassReminder = true;
            if (reminderModal) reminderModal.style.display = 'none';
            if (downloadForm) downloadForm.submit();
        });
    }

const DEFAULT_AVATAR_IMG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0%25' stop-color='%234ea5ff'/><stop offset='50%25' stop-color='%232a85ff'/><stop offset='100%25' stop-color='%231868db'/></linearGradient><linearGradient id='a' x1='0' y1='0' x2='0' y2='1'><stop offset='0%25' stop-color='%23ffffff'/><stop offset='100%25' stop-color='%23e2edfc'/></linearGradient></defs><circle cx='50' cy='50' r='50' fill='url(%23g)'/><circle cx='50' cy='37' r='15' fill='url(%23a)'/><path d='M 23.5 80 C 23.5 63 35 56 50 56 C 65 56 76.5 63 76.5 80 Z' fill='url(%23a)'/></svg>";

function uploadAvatarFromDevice(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(evt) {
            const dataUrl = evt.target.result;
            document.getElementById('previewAvatar').src = dataUrl;
            document.getElementById('dockAvatarImg').src = dataUrl;
            
            // MongoDB Database ma save karvu
            fetch('/api/admin/avatar/upload', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ avatar_url: dataUrl })
            });
        };
        reader.readAsDataURL(file);
    }
}

function removeAdminAvatar() {
    if (confirm('Are you sure you want to remove your custom photo and reset to default?')) {
        fetch('/api/admin/avatar/remove', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            document.getElementById('previewAvatar').src = data.default_avatar || DEFAULT_AVATAR_IMG;
            document.getElementById('dockAvatarImg').src = data.default_avatar || DEFAULT_AVATAR_IMG;
            document.getElementById('avatarFileInput').value = '';
            alert('Profile picture removed and reset to default successfully.');
        });
    }
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
