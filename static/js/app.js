// EcoTrack AI - Frontend Orchestrator

// State variables
let currentUser = null;
let currentView = 'dashboard';
let trendChartInstance = null;
let breakdownChartInstance = null;

// Dom Content Loaded Entry Point
document.addEventListener('DOMContentLoaded', () => {
    // Set default date in calculator to today
    const dateInput = document.getElementById('calc-date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
    }
    
    // Check user session
    checkSession();
});

// Session Management
async function checkSession() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.status === 200) {
            const data = await res.json();
            currentUser = data;
            setupLoggedState();
        } else {
            setupLoggedOutState();
        }
    } catch (e) {
        console.error("Session check failed", e);
        setupLoggedOutState();
    }
}

function setupLoggedState() {
    document.getElementById('view-auth').classList.add('hidden');
    document.getElementById('view-dashboard-shell').classList.remove('hidden');
    document.getElementById('sidebar-username').innerText = currentUser.username;
    document.getElementById('sidebar-avatar').innerText = currentUser.username.charAt(0).toUpperCase();
    document.getElementById('dash-greeting-name').innerText = currentUser.username;
    
    navigateTo('dashboard');
}

function setupLoggedOutState() {
    currentUser = null;
    document.getElementById('view-dashboard-shell').classList.add('hidden');
    document.getElementById('view-auth').classList.remove('hidden');
    toggleAuthForm('login');
}

// Auth UI Toggle
function toggleAuthForm(formType) {
    const loginForm = document.getElementById('form-login');
    const registerForm = document.getElementById('form-register');
    const loginTab = document.getElementById('tab-login-btn');
    const registerTab = document.getElementById('tab-register-btn');
    
    if (formType === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        loginTab.classList.remove('active');
        registerTab.classList.add('active');
    }
}

// Handle Forms
async function handleLogin(e) {
    e.preventDefault();
    const usernameInput = document.getElementById('login-username').value;
    const passwordInput = document.getElementById('login-password').value;
    
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameInput, password: passwordInput })
        });
        
        const data = await res.json();
        if (res.status === 200) {
            showToast("Welcome to EcoTrack AI!");
            currentUser = { username: data.user.username };
            setupLoggedState();
            // Clear inputs
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';
        } else {
            showToast(data.error || "Login failed.");
        }
    } catch (err) {
        showToast("Server connection error.");
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const usernameInput = document.getElementById('reg-username').value;
    const emailInput = document.getElementById('reg-email').value;
    const passwordInput = document.getElementById('reg-password').value;
    
    if (passwordInput.length < 6) {
        showToast("Password must be at least 6 characters.");
        return;
    }
    
    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameInput, email: emailInput, password: passwordInput })
        });
        
        const data = await res.json();
        if (res.status === 200) {
            showToast("Registration successful!");
            currentUser = { username: data.user.username };
            setupLoggedState();
            // Clear inputs
            document.getElementById('reg-username').value = '';
            document.getElementById('reg-email').value = '';
            document.getElementById('reg-password').value = '';
        } else {
            showToast(data.error || "Sign up failed.");
        }
    } catch (err) {
        showToast("Server connection error.");
    }
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        showToast("Logged out successfully.");
        setupLoggedOutState();
    } catch (e) {
        showToast("Failed to logout cleanly.");
    }
}

// Navigation Routines
function navigateTo(viewName) {
    currentView = viewName;
    
    // Hide all subviews
    document.querySelectorAll('.sub-view').forEach(v => v.classList.add('hidden'));
    
    // Remove active styles from nav links
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    
    // Show selected subview
    const targetView = document.getElementById(`subview-${viewName}`);
    if (targetView) targetView.classList.remove('hidden');
    
    // Highlight sidebar active tab
    const navItem = document.querySelector(`.nav-item[data-view="${viewName}"]`);
    if (navItem) navItem.classList.add('active');
    
    // Sync mobile menu active links
    document.querySelectorAll('.mobile-nav-item').forEach(mi => {
        if (mi.getAttribute('data-view') === viewName) {
            mi.classList.add('active');
        } else {
            mi.classList.remove('active');
        }
    });

    // Close mobile menu if open
    document.getElementById('mobile-nav').classList.add('hidden');
    
    // Load fresh data for view
    loadViewData(viewName);
}

// Mobile specific navigation (closes drawer automatically)
function navigateToMobile(viewName) {
    navigateTo(viewName);
    toggleMobileMenu();
}

function toggleMobileMenu() {
    const mobileNav = document.getElementById('mobile-nav');
    mobileNav.classList.toggle('hidden');
}

// Synchronize range sliders text values
function syncSliderVal(sliderId, textId) {
    const slider = document.getElementById(sliderId);
    const textSpan = document.getElementById(textId);
    if (slider && textSpan) {
        const unit = sliderId.includes('miles') ? ' miles' : ' kWh';
        textSpan.innerText = slider.value + unit;
    }
}

// Reroute view loading to APIs
function loadViewData(viewName) {
    switch (viewName) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'log-activity':
            resetCalculatorForm();
            break;
        case 'recommendations':
            loadRecommendations();
            break;
        case 'achievements':
            loadAchievements();
            break;
        case 'profile':
            loadProfileDetails();
            break;
    }
}

// ================= VIEW: DASHBOARD =================
async function loadDashboardData() {
    try {
        const res = await fetch('/api/dashboard');
        if (res.status === 401) {
            setupLoggedOutState();
            return;
        }
        
        const data = await res.json();
        
        // Update KPI values
        document.getElementById('kpi-today').innerHTML = `${data.today.toFixed(1)} <span class="unit">kg CO₂</span>`;
        document.getElementById('kpi-weekly').innerHTML = `${data.weekly.toFixed(1)} <span class="unit">kg CO₂</span>`;
        document.getElementById('kpi-monthly').innerHTML = `${data.monthly.toFixed(1)} <span class="unit">kg CO₂</span>`;
        document.getElementById('kpi-goal').innerHTML = `${data.daily_goal.toFixed(1)} <span class="unit">kg CO₂</span>`;
        
        // Update daily progress limit
        const progressBar = document.getElementById('goal-progress-bar');
        const progressPercentageText = document.getElementById('goal-percentage-text');
        const helperMessage = document.getElementById('goal-helper-message');
        
        let percentage = 0;
        if (data.daily_goal > 0) {
            percentage = Math.round((data.today / data.daily_goal) * 100);
        }
        
        progressBar.style.width = `${Math.min(percentage, 100)}%`;
        progressPercentageText.innerText = `${percentage}% Limit Used`;
        
        if (percentage === 0) {
            progressBar.className = "progress-bar";
            helperMessage.innerText = "Log today's activities to check your emissions limit.";
        } else if (percentage <= 100) {
            progressBar.className = "progress-bar";
            helperMessage.innerText = `Great job! You have ${data.daily_goal - data.today > 0 ? (data.daily_goal - data.today).toFixed(1) : 0} kg remaining today to stay within your goal.`;
        } else {
            progressBar.className = "progress-bar over-limit";
            helperMessage.innerText = `You exceeded your daily carbon target by ${(data.today - data.daily_goal).toFixed(1)} kg. Try a recommendation to offset!`;
        }
        
        // Render charts
        renderTrendChart(data.history);
        renderBreakdownChart(data.breakdown);
        
        // Render recent activity table
        const recentTable = document.getElementById('dashboard-recent-table');
        if (data.recent.length === 0) {
            recentTable.innerHTML = `<tr><td colspan="3" class="empty-state">No logs recorded yet. Start tracking below!</td></tr>`;
        } else {
            recentTable.innerHTML = data.recent.map(r => {
                const isUnder = r.emissions <= data.daily_goal;
                const badgeClass = isUnder ? 'badge-under-goal' : 'badge-over-goal';
                const badgeText = isUnder ? 'Under Goal' : 'Over Limit';
                
                return `
                    <tr>
                        <td><i class="fa-regular fa-calendar-check text-accent"></i> ${formatDateLabel(r.date)}</td>
                        <td><strong>${r.emissions.toFixed(1)} kg CO₂</strong></td>
                        <td><span class="badge-status ${badgeClass}">${badgeText}</span></td>
                    </tr>
                `;
            }).join('');
        }
        
    } catch (e) {
        showToast("Error loading dashboard indicators.");
    }
}

// Chart Rendering Logic
function renderTrendChart(historyData) {
    const ctx = document.getElementById('chart-emissions-trend').getContext('2d');
    
    // Destroy existing instance to avoid overlap bugs
    if (trendChartInstance) {
        trendChartInstance.destroy();
    }
    
    const labels = historyData.map(h => h.label);
    const dataPoints = historyData.map(h => h.emissions);
    
    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Daily Footprint',
                data: dataPoints,
                borderColor: '#05c46b',
                backgroundColor: 'rgba(5, 196, 107, 0.08)',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: '#05c46b',
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#a5b1be' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#a5b1be' }
                }
            }
        }
    });
}

function renderBreakdownChart(breakdownData) {
    const ctx = document.getElementById('chart-category-breakdown').getContext('2d');
    
    if (breakdownChartInstance) {
        breakdownChartInstance.destroy();
    }
    
    const values = [breakdownData.transportation, breakdownData.electricity, breakdownData.diet];
    const isAllZero = values.reduce((a, b) => a + b, 0) === 0;
    
    // If no values, render placeholders so chart isn't blank
    const chartData = isAllZero ? [1, 1, 1] : values;
    const chartColors = isAllZero 
        ? ['rgba(255,255,255,0.05)', 'rgba(255,255,255,0.05)', 'rgba(255,255,255,0.05)']
        : ['#00d2d3', '#ffd32a', '#05c46b'];
        
    breakdownChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Transportation', 'Electricity', 'Diet'],
            datasets: [{
                data: chartData,
                backgroundColor: chartColors,
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#a5b1be', font: { size: 10 } }
                },
                tooltip: {
                    enabled: !isAllZero
                }
            },
            cutout: '70%'
        }
    });
}

// Helper dates parsing
function formatDateLabel(dateString) {
    try {
        const parts = dateString.split('-');
        const dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
        return dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch(e) {
        return dateString;
    }
}

// ================= VIEW: LOG FOOTPRINT (CALCULATOR) =================
function resetCalculatorForm() {
    document.getElementById('calc-transport-type').value = 'active';
    document.getElementById('calc-transport-miles').value = 0;
    syncSliderVal('calc-transport-miles', 'val-miles');
    
    document.getElementById('calc-electricity').value = 0;
    syncSliderVal('calc-electricity', 'val-elec');
    
    // Select average diet
    const averageRadio = document.querySelector('input[name="calc-diet"][value="average"]');
    if (averageRadio) averageRadio.checked = true;
    
    // Date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('calc-date').value = today;
    
    updateLiveEstimation();
}

// Live estimates logic
function updateLiveEstimation() {
    const tType = document.getElementById('calc-transport-type').value;
    const tMiles = parseFloat(document.getElementById('calc-transport-miles').value) || 0;
    const eKwh = parseFloat(document.getElementById('calc-electricity').value) || 0;
    
    // Read selected diet radio button
    const dietRadio = document.querySelector('input[name="calc-diet"]:checked');
    const dType = dietRadio ? dietRadio.value : 'average';
    
    // Calculation factors matching python calculator
    const transportFactors = {
        'gasoline_car': 0.411,
        'electric_car': 0.110,
        'public_transit': 0.140,
        'flight': 0.240,
        'active': 0.0
    };
    const elecFactor = 0.390;
    const dietFactors = {
        'vegan': 2.9,
        'vegetarian': 3.8,
        'average': 5.6,
        'meat_heavy': 7.2
    };
    
    const transportCO2 = tMiles * (transportFactors[tType] || 0.0);
    const electricityCO2 = eKwh * elecFactor;
    const dietCO2 = dietFactors[dType] || 5.6;
    const totalCO2 = transportCO2 + electricityCO2 + dietCO2;
    
    // Update live widget details
    document.getElementById('live-co2-val').innerText = totalCO2.toFixed(2);
    document.getElementById('live-breakdown-transport').innerText = `${transportCO2.toFixed(2)} kg`;
    document.getElementById('live-breakdown-electricity').innerText = `${electricityCO2.toFixed(2)} kg`;
    document.getElementById('live-breakdown-diet').innerText = `${dietCO2.toFixed(2)} kg`;
}

async function submitFootprint(e) {
    e.preventDefault();
    
    const date = document.getElementById('calc-date').value;
    const tType = document.getElementById('calc-transport-type').value;
    const tMiles = parseFloat(document.getElementById('calc-transport-miles').value);
    const eKwh = parseFloat(document.getElementById('calc-electricity').value);
    
    const dietRadio = document.querySelector('input[name="calc-diet"]:checked');
    const dType = dietRadio ? dietRadio.value : 'average';
    
    try {
        const res = await fetch('/api/footprint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: date,
                transport_miles: tMiles,
                transport_type: tType,
                electricity_kwh: eKwh,
                diet_type: dType
            })
        });
        
        const data = await res.json();
        if (res.status === 200) {
            showToast("Carbon footprint logged successfully.");
            
            // Check for achievement unlocks
            if (data.newly_unlocked && data.newly_unlocked.length > 0) {
                // If multiple badges, show them sequential or just the first
                showAchievementModal(data.newly_unlocked[0]);
            }
            
            // Navigate back to Dashboard
            navigateTo('dashboard');
        } else {
            showToast(data.error || "Failed to log emissions.");
        }
    } catch (err) {
        showToast("Error connecting to server.");
    }
}

// ================= VIEW: RECOMMENDATIONS =================
async function loadRecommendations() {
    const listContainer = document.getElementById('recommendations-list');
    listContainer.innerHTML = `
        <div class="loading-state card">
            <div class="spinner"></div>
            <p>Analyzing emissions and fetching recommendations...</p>
        </div>
    `;
    
    try {
        const res = await fetch('/api/recommendations');
        if (res.status === 401) {
            setupLoggedOutState();
            return;
        }
        
        const recs = await res.json();
        renderRecommendations(recs);
    } catch (e) {
        listContainer.innerHTML = `<div class="card"><p class="empty-state">Error loading recommendations.</p></div>`;
    }
}

function renderRecommendations(recs) {
    const listContainer = document.getElementById('recommendations-list');
    if (recs.length === 0) {
        listContainer.innerHTML = `
            <div class="card">
                <p class="empty-state">No recommendations right now. Track more days to help Gemini AI personalize suggestions!</p>
            </div>
        `;
        return;
    }
    
    listContainer.innerHTML = recs.map(r => {
        let iconHtml = '';
        if (r.category === 'transportation') iconHtml = '<i class="fa-solid fa-car-side"></i>';
        else if (r.category === 'electricity') iconHtml = '<i class="fa-solid fa-bolt"></i>';
        else iconHtml = '<i class="fa-solid fa-utensils"></i>';
        
        const completedClass = r.completed ? 'completed' : '';
        
        return `
            <div class="rec-card ${completedClass}" id="rec-card-${r.id}">
                <div class="rec-info-wrapper">
                    <div class="rec-badge-icon badge-${r.category}">${iconHtml}</div>
                    <span class="rec-text">${r.suggestion}</span>
                </div>
                <button class="checkbox-btn" onclick="completeRecommendation(${r.id})" title="Mark complete">
                    <i class="fa-solid fa-check"></i>
                </button>
            </div>
        `;
    }).join('');
}

async function generateNewRecommendations() {
    const btn = document.getElementById('btn-refresh-recs');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...`;
    
    const listContainer = document.getElementById('recommendations-list');
    listContainer.innerHTML = `
        <div class="loading-state card">
            <div class="spinner"></div>
            <p>Consulting Gemini AI based on your latest activities...</p>
        </div>
    `;
    
    try {
        const res = await fetch('/api/recommendations/generate', { method: 'POST' });
        const recs = await res.json();
        renderRecommendations(recs);
        showToast("Recommendations updated!");
    } catch (e) {
        showToast("Failed to request fresh ideas.");
        loadRecommendations();
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Refresh AI Tips`;
    }
}

async function completeRecommendation(id) {
    const card = document.getElementById(`rec-card-${id}`);
    if (!card || card.classList.contains('completed')) return;
    
    try {
        const res = await fetch(`/api/recommendations/${id}/complete`, { method: 'POST' });
        const data = await res.json();
        
        if (res.status === 200) {
            card.classList.add('completed');
            showToast("Action logged! Thank you for reducing emissions.");
            
            // Check for achievement unlocks
            if (data.newly_unlocked && data.newly_unlocked.length > 0) {
                showAchievementModal(data.newly_unlocked[0]);
            }
            
            // Reload recommendations after 1s delay
            setTimeout(loadRecommendations, 1000);
        } else {
            showToast("Failed to lock in completion.");
        }
    } catch (e) {
        showToast("Connection issue logging completion.");
    }
}

// ================= VIEW: ACHIEVEMENTS =================
async function loadAchievements() {
    const container = document.getElementById('achievements-container');
    container.innerHTML = `
        <div class="loading-state card" style="grid-column: 1 / -1;">
            <div class="spinner"></div>
            <p>Checking badge requirements...</p>
        </div>
    `;
    
    try {
        const res = await fetch('/api/achievements');
        const data = await res.json();
        
        container.innerHTML = data.map(ach => {
            const unlockedClass = ach.unlocked ? 'unlocked' : '';
            const statusTag = ach.unlocked 
                ? `<span class="unlocked-tag"><i class="fa-solid fa-lock-open"></i> Unlocked</span>` 
                : `<span class="unlocked-tag" style="color: var(--text-muted);"><i class="fa-solid fa-lock"></i> Locked</span>`;
                
            return `
                <div class="achievement-card ${unlockedClass}">
                    ${statusTag}
                    <div class="badge-wrapper">${ach.badge_icon}</div>
                    <div class="ach-details">
                        <h3>${ach.name}</h3>
                        <p>${ach.description}</p>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = `<p class="empty-state" style="grid-column: 1 / -1;">Failed to load achievements.</p>`;
    }
}

// ================= VIEW: PROFILE =================
async function loadProfileDetails() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.status === 200) {
            const data = await res.json();
            currentUser = data;
            
            document.getElementById('profile-username').value = data.username;
            document.getElementById('profile-email').value = data.email;
            document.getElementById('profile-goal').value = data.daily_goal;
        }
    } catch (e) {
        showToast("Error updating settings forms.");
    }
}

async function updateProfile(e) {
    e.preventDefault();
    const email = document.getElementById('profile-email').value;
    const goal = parseFloat(document.getElementById('profile-goal').value);
    const password = document.getElementById('profile-password').value;
    
    const bodyObj = { email: email, daily_goal: goal };
    if (password) {
        bodyObj.password = password;
    }
    
    try {
        const res = await fetch('/api/auth/me', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bodyObj)
        });
        
        const data = await res.json();
        if (res.status === 200) {
            showToast("Settings updated successfully!");
            currentUser.email = email;
            currentUser.daily_goal = goal;
            
            // Reset password field
            document.getElementById('profile-password').value = '';
        } else {
            showToast(data.error || "Failed to update profile settings.");
        }
    } catch (err) {
        showToast("Server communication error.");
    }
}

// ================= POPUPS, TOASTS & MODALS =================
function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.innerText = message;
    toast.classList.remove('hidden');
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 4000);
}

function showAchievementModal(badge) {
    const modal = document.getElementById('achievement-modal');
    document.getElementById('modal-badge-icon').innerText = badge.badge_icon;
    document.getElementById('modal-badge-name').innerText = badge.name;
    document.getElementById('modal-badge-desc').innerText = badge.description;
    
    modal.classList.remove('hidden');
}

function closeAchievementModal() {
    document.getElementById('achievement-modal').classList.add('hidden');
}
