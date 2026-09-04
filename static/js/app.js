/**
 * CareSync - Main SPA Application Controller
 */

// Application State
const state = {
    user: null,
    activePage: 'dashboard',
    patients: [],
    patientsPage: 1,
    patientsLimit: 10,
    patientsTotal: 0,
    patientsSearch: '',
    patientsSort: 'patient_id',
    patientsOrder: 'asc',
    activePatient: null,
    users: [],
    logs: [],
    confirmCallback: null,
    
    // AI Portal State
    activeAITab: 'radiology',
    currentAIRadiologyReport: null,
    currentAILabReport: null,
    currentAIClinicalReport: null,
    aiHistoryList: []
};

// ============================================================
// INITIALIZATION & SESSION CHECK
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initDateTime();
    initEventListeners();
    checkSession();
});

function initDateTime() {
    const options = { weekday: 'long', year: 'numeric', month: 'short', day: 'numeric' };
    const dateStr = new Date().toLocaleDateString('en-US', options);
    const dateEl = document.getElementById('header-date');
    if (dateEl) dateEl.textContent = dateStr;
}

async function checkSession() {
    showAppLoader();
    try {
        const sessionData = await window.API.getSession();
        if (sessionData.logged_in) {
            setupUserSession(sessionData.user);
        } else {
            showLoginScreen();
        }
    } catch (err) {
        showToast('System Error', 'Could not establish connection to the server.', 'error');
        showLoginScreen();
    } finally {
        hideAppLoader();
    }
}

function setupUserSession(user) {
    state.user = user;
    
    const appEl = document.getElementById('app');
    appEl.className = 'app-logged-in';
    
    document.getElementById('sidebar-user-name').textContent = user.full_name;
    document.getElementById('sidebar-user-role').textContent = user.role;
    
    renderSidebarNav();
    
    if (user.role === 'Radiologist' || user.role === 'Lab Operator') {
        navigateTo('ai_portal');
    } else {
        navigateTo('dashboard');
    }
    showToast('Welcome Back', `Logged in as ${user.full_name}`, 'success');
}

function showLoginScreen() {
    state.user = null;
    const appEl = document.getElementById('app');
    appEl.className = 'app-logged-out';
    document.getElementById('login-username').value = '';
    document.getElementById('login-password').value = '';
}

function fillLogin(username, password) {
    document.getElementById('login-username').value = username;
    document.getElementById('login-password').value = password;
    showToast('Demo Credentials', `Filled login for: ${username}`, 'info', 2000);
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function showToast(title, message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconClass = 'fa-solid fa-circle-info';
    if (type === 'success') iconClass = 'fa-solid fa-circle-check';
    if (type === 'error') iconClass = 'fa-solid fa-circle-exclamation';
    if (type === 'warning') iconClass = 'fa-solid fa-triangle-exclamation';

    toast.innerHTML = `
        <i class="${iconClass} toast-icon"></i>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.style.animation = 'toast-out 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    });

    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'toast-out 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// ============================================================
// MODAL CONTROLS
// ============================================================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('active'), 10);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

function openConfirmModal(message, onConfirm) {
    document.getElementById('confirm-modal-message').textContent = message;
    state.confirmCallback = onConfirm;
    openModal('confirm-modal');
}

// ============================================================
// SIDEBAR & PAGE NAVIGATION
// ============================================================
function renderSidebarNav() {
    const linksContainer = document.getElementById('nav-links');
    if (!linksContainer) return;
    
    let links = [];
    const role = state.user.role;
    
    if (role === 'Admin') {
        links = [
            { id: 'dashboard', label: 'Overview Dashboard', icon: 'fa-solid fa-chart-line' },
            { id: 'patients', label: 'Patient Registry', icon: 'fa-solid fa-hospital-user' },
            { id: 'ai_portal', label: 'AI Diagnostic Portal', icon: 'fa-solid fa-wand-magic-sparkles', highlight: true },
            { id: 'users', label: 'User Management', icon: 'fa-solid fa-users-gear' },
            { id: 'logs', label: 'System Activity Logs', icon: 'fa-solid fa-clock-rotate-left' }
        ];
    } else if (role === 'Doctor') {
        links = [
            { id: 'dashboard', label: 'Clinician Dashboard', icon: 'fa-solid fa-user-md' },
            { id: 'patients', label: 'My Patients', icon: 'fa-solid fa-notes-medical' },
            { id: 'ai_portal', label: 'AI Diagnostic Portal', icon: 'fa-solid fa-wand-magic-sparkles', highlight: true }
        ];
    } else if (role === 'Receptionist') {
        links = [
            { id: 'dashboard', label: 'Reception Dashboard', icon: 'fa-solid fa-hospital-user' },
            { id: 'patients', label: 'Patient Registry', icon: 'fa-solid fa-address-book' }
        ];
    } else if (role === 'Nurse') {
        links = [
            { id: 'dashboard', label: 'Nursing Dashboard', icon: 'fa-solid fa-user-nurse' },
            { id: 'patients', label: 'Patient Vitals Care', icon: 'fa-solid fa-heart-pulse' }
        ];
    } else if (role === 'Radiologist') {
        links = [
            { id: 'dashboard', label: 'Radiology Dashboard', icon: 'fa-solid fa-x-ray' },
            { id: 'ai_portal', label: 'AI Radiology Portal', icon: 'fa-solid fa-wand-magic-sparkles', highlight: true }
        ];
    } else if (role === 'Lab Operator') {
        links = [
            { id: 'dashboard', label: 'Lab Dashboard', icon: 'fa-solid fa-flask-vial' },
            { id: 'ai_portal', label: 'AI Lab Report Portal', icon: 'fa-solid fa-wand-magic-sparkles', highlight: true }
        ];
    }
    
    linksContainer.innerHTML = links.map(link => `
        <li>
            <button class="nav-link w-100 ${link.highlight ? 'ai-highlight' : ''}" data-page="${link.id}">
                <i class="${link.icon}"></i>
                <span>${link.label}</span>
            </button>
        </li>
    `).join('');
    
    linksContainer.querySelectorAll('.nav-link').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const page = e.currentTarget.getAttribute('data-page');
            navigateTo(page);
            
            const sidebar = document.getElementById('sidebar');
            if (sidebar.classList.contains('sidebar-open')) {
                sidebar.classList.remove('sidebar-open');
                document.body.classList.remove('sidebar-overlay-active');
            }
        });
    });
}

function navigateTo(pageId) {
    state.activePage = pageId;
    
    document.querySelectorAll('.nav-link').forEach(btn => {
        if (btn.getAttribute('data-page') === pageId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    const breadcrumbActive = document.getElementById('breadcrumb-active');
    let pageLabel = 'Dashboard';
    if (pageId === 'users') pageLabel = 'User Management';
    if (pageId === 'logs') pageLabel = 'Activity Logs';
    if (pageId === 'patients') pageLabel = 'Patient System';
    if (pageId === 'ai_portal') pageLabel = 'AI Diagnostic Portal';
    breadcrumbActive.textContent = pageLabel;
    
    loadPageView(pageId);
}

// ============================================================
// VIEW DISPATCHER
// ============================================================
function loadPageView(pageId) {
    const container = document.getElementById('page-content');
    container.innerHTML = `<div class="spinner-wrapper"><div class="spinner"></div></div>`;
    
    if (pageId === 'dashboard') {
        renderDashboardView();
    } else if (pageId === 'users') {
        renderUsersView();
    } else if (pageId === 'logs') {
        renderLogsView();
    } else if (pageId === 'patients') {
        renderPatientsView();
    } else if (pageId === 'ai_portal') {
        renderAIPortalView();
    }
}

// ============================================================
// VIEW 1: DASHBOARD OVERVIEW
// ============================================================
async function renderDashboardView() {
    const container = document.getElementById('page-content');
    const role = state.user.role;
    
    try {
        const stats = await window.API.getStats();
        
        let statsHtml = '';
        let innerHtml = '';
        
        if (role === 'Admin') {
            statsHtml = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon teal"><i class="fa-solid fa-users"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_users || 0}</span>
                            <span class="stat-label">Total Staff Accounts</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-user-check"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.active_users || 0}</span>
                            <span class="stat-label">Active Users</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fa-solid fa-hospital-user"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_patients || 0}</span>
                            <span class="stat-label">Total Patients</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_ai_reports || 0}</span>
                            <span class="stat-label">AI Diagnostic Reports</span>
                        </div>
                    </div>
                </div>
            `;
            
            const logs = await window.API.getLogs();
            const recentLogs = logs.slice(0, 5);
            
            innerHtml = `
                <div class="layout-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-clock-rotate-left"></i> Recent Activity Logs</h3>
                            <button class="btn btn-outline btn-sm" onclick="navigateTo('logs')">View All</button>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Timestamp</th>
                                            <th>User</th>
                                            <th>Role</th>
                                            <th>Action</th>
                                            <th>Details</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${recentLogs.map(log => `
                                            <tr>
                                                <td class="text-muted">${formatDate(log.created_at)}</td>
                                                <td><strong>${log.username || 'System'}</strong></td>
                                                <td><span class="role-badge">${log.role || 'System'}</span></td>
                                                <td><strong>${log.action}</strong></td>
                                                <td>${log.details || ''}</td>
                                            </tr>
                                        `).join('') || '<tr><td colspan="5" class="text-center text-muted">No logs recorded yet.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-circle-info"></i> System Shortcuts</h3>
                        </div>
                        <div class="card-body">
                            <div style="display:flex; flex-direction:column; gap:12px;">
                                <button class="btn btn-ai btn-block text-left" onclick="navigateTo('ai_portal')">
                                    <i class="fa-solid fa-wand-magic-sparkles"></i> AI Diagnostic Portal
                                </button>
                                <button class="btn btn-primary btn-block text-left" onclick="showCreateUserForm()">
                                    <i class="fa-solid fa-user-plus"></i> Create Staff Account
                                </button>
                                <button class="btn btn-outline btn-block text-left" onclick="navigateTo('users')">
                                    <i class="fa-solid fa-users-gear"></i> Manage Staff List
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
        } else if (role === 'Doctor') {
            statsHtml = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon teal"><i class="fa-solid fa-hospital-user"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_patients || 0}</span>
                            <span class="stat-label">Total Patients</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-stethoscope"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.diagnoses_today || 0}</span>
                            <span class="stat-label">Diagnoses Today</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fa-solid fa-prescription-bottle-medical"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.prescriptions_today || 0}</span>
                            <span class="stat-label">Prescriptions Today</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.my_ai_analyses || 0}</span>
                            <span class="stat-label">My AI Diagnostic Sessions</span>
                        </div>
                    </div>
                </div>
            `;
            
            const pResponse = await window.API.getPatients({ limit: 5 });
            const patientList = pResponse.patients;
            
            innerHtml = `
                <div class="layout-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-clipboard-list"></i> Select Patient for Clinical Consultation</h3>
                            <button class="btn btn-outline btn-sm" onclick="navigateTo('patients')">View All</button>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Patient ID</th>
                                            <th>Full Name</th>
                                            <th>DOB</th>
                                            <th>Gender</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${patientList.map(p => `
                                            <tr>
                                                <td><span class="role-badge">${p.patient_id}</span></td>
                                                <td><strong>${p.full_name}</strong></td>
                                                <td>${p.dob}</td>
                                                <td>${p.gender}</td>
                                                <td>
                                                    <button class="btn btn-secondary btn-sm" onclick="viewPatientProfile('${p.patient_id}')">
                                                        <i class="fa-solid fa-stethoscope"></i> View Case File & AI
                                                    </button>
                                                </td>
                                            </tr>
                                        `).join('') || '<tr><td colspan="5" class="text-center text-muted">No patients registered.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-wand-magic-sparkles"></i> AI Diagnostics</h3>
                        </div>
                        <div class="card-body">
                            <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:15px;">Analyze X-Rays, scan lab results, or generate differential diagnoses with the AI Clinical Decision Assistant.</p>
                            <button class="btn btn-ai btn-block" onclick="navigateTo('ai_portal')">
                                <i class="fa-solid fa-microscope"></i> Open AI Diagnostic Portal
                            </button>
                        </div>
                    </div>
                </div>
            `;
        } else if (role === 'Radiologist') {
            statsHtml = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon teal"><i class="fa-solid fa-x-ray"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_radiology_reports || 0}</span>
                            <span class="stat-label">Total Radiology Scans</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-circle-check"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.accepted_radiology || 0}</span>
                            <span class="stat-label">Verified & Accepted</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fa-solid fa-user-doctor"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.my_radiology_reports || 0}</span>
                            <span class="stat-label">Processed By Me</span>
                        </div>
                    </div>
                </div>
            `;
            innerHtml = `
                <div class="card">
                    <div class="card-body text-center" style="padding: 40px 20px;">
                        <i class="fa-solid fa-x-ray" style="font-size:3rem; color:var(--primary); margin-bottom:15px;"></i>
                        <h3>AI Radiology Workstation Ready</h3>
                        <p class="text-muted" style="max-width:500px; margin: 10px auto 20px;">Upload DICOM/X-Rays/MRI scans for real-time automated pathology detection and structured differential diagnosis.</p>
                        <button class="btn btn-ai btn-lg" onclick="navigateTo('ai_portal')"><i class="fa-solid fa-wand-magic-sparkles"></i> Launch Radiology Analyzer</button>
                    </div>
                </div>
            `;
        } else if (role === 'Lab Operator') {
            statsHtml = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon teal"><i class="fa-solid fa-flask-vial"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_lab_reports || 0}</span>
                            <span class="stat-label">Total Lab Reports</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-circle-check"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.accepted_lab || 0}</span>
                            <span class="stat-label">Verified & Accepted</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fa-solid fa-user-gear"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.my_lab_reports || 0}</span>
                            <span class="stat-label">Processed By Me</span>
                        </div>
                    </div>
                </div>
            `;
            innerHtml = `
                <div class="card">
                    <div class="card-body text-center" style="padding: 40px 20px;">
                        <i class="fa-solid fa-flask-vial" style="font-size:3rem; color:var(--primary); margin-bottom:15px;"></i>
                        <h3>AI Lab Report Analyzer Ready</h3>
                        <p class="text-muted" style="max-width:500px; margin: 10px auto 20px;">Upload or paste blood panels and urinalysis data to extract abnormal reference ranges and critical values.</p>
                        <button class="btn btn-ai btn-lg" onclick="navigateTo('ai_portal')"><i class="fa-solid fa-wand-magic-sparkles"></i> Launch Lab Analyzer</button>
                    </div>
                </div>
            `;
        } else if (role === 'Receptionist') {
            statsHtml = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon teal"><i class="fa-solid fa-address-book"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_patients || 0}</span>
                            <span class="stat-label">Total Patients</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-calendar-check"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.registered_today || 0}</span>
                            <span class="stat-label">Registered Today</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fa-solid fa-clipboard-user"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.registered_by_me || 0}</span>
                            <span class="stat-label">Registered By Me</span>
                        </div>
                    </div>
                </div>
            `;
            const pResponse = await window.API.getPatients({ limit: 5 });
            const recentPatients = pResponse.patients;
            innerHtml = `
                <div class="layout-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-users"></i> Recently Registered Patients</h3>
                            <button class="btn btn-outline btn-sm" onclick="navigateTo('patients')">View Registry</button>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Patient ID</th>
                                            <th>Full Name</th>
                                            <th>DOB</th>
                                            <th>Gender</th>
                                            <th>Phone</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${recentPatients.map(p => `
                                            <tr>
                                                <td><span class="role-badge">${p.patient_id}</span></td>
                                                <td><strong>${p.full_name}</strong></td>
                                                <td>${p.dob}</td>
                                                <td>${p.gender}</td>
                                                <td>${p.phone}</td>
                                            </tr>
                                        `).join('') || '<tr><td colspan="5" class="text-center text-muted">No patients registered yet.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-circle-info"></i> Quick Actions</h3>
                        </div>
                        <div class="card-body">
                            <div style="display:flex; flex-direction:column; gap:12px;">
                                <button class="btn btn-primary btn-block" onclick="showRegisterPatientForm()">
                                    <i class="fa-solid fa-hospital-user"></i> Register New Patient
                                </button>
                                <button class="btn btn-outline btn-block" onclick="navigateTo('patients')">
                                    <i class="fa-solid fa-magnifying-glass"></i> Search Patients
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (role === 'Nurse') {
            statsHtml = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon teal"><i class="fa-solid fa-hospital-user"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.total_patients || 0}</span>
                            <span class="stat-label">Total Patients</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-heart-pulse"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.vitals_logged_today || 0}</span>
                            <span class="stat-label">Vitals Logged Today</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fa-solid fa-user-nurse"></i></div>
                        <div class="stat-info">
                            <span class="stat-value">${stats.vitals_logged_by_me || 0}</span>
                            <span class="stat-label">Logged By Me</span>
                        </div>
                    </div>
                </div>
            `;
            const pResponse = await window.API.getPatients({ limit: 5 });
            const patientList = pResponse.patients;
            innerHtml = `
                <div class="layout-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-users-medical"></i> Select Patient to Log Vitals</h3>
                            <button class="btn btn-outline btn-sm" onclick="navigateTo('patients')">View All</button>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Patient ID</th>
                                            <th>Full Name</th>
                                            <th>Gender</th>
                                            <th>Phone</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${patientList.map(p => `
                                            <tr>
                                                <td><span class="role-badge">${p.patient_id}</span></td>
                                                <td><strong>${p.full_name}</strong></td>
                                                <td>${p.gender}</td>
                                                <td>${p.phone}</td>
                                                <td>
                                                    <button class="btn btn-primary btn-sm" onclick="viewPatientProfile('${p.patient_id}')">
                                                        <i class="fa-solid fa-heart-pulse"></i> View & Log
                                                    </button>
                                                </td>
                                            </tr>
                                        `).join('') || '<tr><td colspan="5" class="text-center text-muted">No patients registered.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-shield-halved"></i> Nurse Guidelines</h3>
                        </div>
                        <div class="card-body" style="font-size:0.875rem;">
                            <p style="margin-bottom:10px;"><i class="fa-solid fa-check text-success"></i> Search patients and record vital signs.</p>
                            <p><i class="fa-solid fa-ban text-danger"></i> Clinical notes and physician diagnoses are protected by role privacy.</p>
                        </div>
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = `
            <div class="dashboard-title-row">
                <h2>Overview Dashboard (${role})</h2>
            </div>
            ${statsHtml}
            ${innerHtml}
        `;
        
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-triangle-exclamation empty-state-icon text-danger"></i>
                <h4>Failed to load dashboard data</h4>
                <p>${err.message}</p>
                <button class="btn btn-outline btn-sm mt-3" onclick="navigateTo('dashboard')">Try Again</button>
            </div>
        `;
    }
}

// ============================================================
// VIEW 2: AI DIAGNOSTIC PORTAL
// ============================================================
function renderAIPortalView() {
    const container = document.getElementById('page-content');
    const role = state.user.role;
    
    const canSeeRadio = ['Doctor', 'Radiologist', 'Admin'].includes(role);
    const canSeeLab = ['Doctor', 'Lab Operator', 'Admin'].includes(role);

    if (!canSeeRadio && state.activeAITab === 'radiology') {
        state.activeAITab = 'lab';
    }
    if (!canSeeLab && state.activeAITab === 'lab') {
        state.activeAITab = 'radiology';
    }

    container.innerHTML = `
        <div class="dashboard-title-row">
            <div>
                <h2><i class="fa-solid fa-wand-magic-sparkles text-primary"></i> AI Diagnostic Portal</h2>
                <p class="text-muted" style="font-size:0.875rem;">AI-Powered Computer Vision & Clinical Decision Support Systems</p>
            </div>
        </div>

        <div class="portal-nav-tabs">
            ${canSeeRadio ? `
                <button class="portal-tab-btn ${state.activeAITab === 'radiology' ? 'active' : ''}" onclick="switchAITab('radiology')">
                    <i class="fa-solid fa-x-ray"></i> AI Radiology Analyzer
                </button>
            ` : ''}
            ${canSeeLab ? `
                <button class="portal-tab-btn ${state.activeAITab === 'lab' ? 'active' : ''}" onclick="switchAITab('lab')">
                    <i class="fa-solid fa-flask-vial"></i> AI Lab Report Analyzer
                </button>
            ` : ''}
            <button class="portal-tab-btn ${state.activeAITab === 'history' ? 'active' : ''}" onclick="switchAITab('history')">
                <i class="fa-solid fa-clock-rotate-left"></i> AI Diagnostic History
            </button>
        </div>

        <div id="ai-tab-content"></div>
    `;

    renderAITabContent();
}

function switchAITab(tabName) {
    state.activeAITab = tabName;
    document.querySelectorAll('.portal-tab-btn').forEach(btn => btn.classList.remove('active'));
    renderAITabContent();
    
    document.querySelectorAll('.portal-tab-btn').forEach(btn => {
        if (btn.textContent.toLowerCase().includes(tabName)) {
            btn.classList.add('active');
        }
    });
}

function renderAITabContent() {
    const tabContainer = document.getElementById('ai-tab-content');
    if (!tabContainer) return;

    if (state.activeAITab === 'radiology') {
        renderRadiologyTab(tabContainer);
    } else if (state.activeAITab === 'lab') {
        renderLabTab(tabContainer);
    } else if (state.activeAITab === 'history') {
        renderAIHistoryTab(tabContainer);
    }
}

// ------------------------------------------------------------
// TAB 1: AI RADIOLOGY ANALYZER
// ------------------------------------------------------------
function renderRadiologyTab(container) {
    container.innerHTML = `
        <div class="layout-grid">
            <div class="card card-glass">
                <div class="card-header">
                    <h3><i class="fa-solid fa-upload"></i> Upload Diagnostic Image (X-Ray / MRI / CT)</h3>
                </div>
                <div class="card-body">
                    <form id="ai-radiology-form">
                        <div class="form-row">
                            <div class="form-group col-6">
                                <label for="radio-patient-id">Associate with Patient ID (Optional)</label>
                                <input type="text" id="radio-patient-id" placeholder="e.g. PAT-0001">
                            </div>
                            <div class="form-group col-3">
                                <label for="radio-modality">Modality *</label>
                                <select id="radio-modality" required>
                                    <option value="X-Ray" selected>X-Ray</option>
                                    <option value="CT Scan">CT Scan</option>
                                    <option value="MRI">MRI</option>
                                    <option value="Ultrasound">Ultrasound</option>
                                </select>
                            </div>
                            <div class="form-group col-3">
                                <label for="radio-body-part">Anatomical Region *</label>
                                <select id="radio-body-part" required>
                                    <option value="Chest" selected>Chest / Thorax</option>
                                    <option value="Brain">Brain / Head</option>
                                    <option value="Bone / Extremity">Bone / Extremity</option>
                                    <option value="Abdomen">Abdomen / Pelvis</option>
                                    <option value="Spine">Spine</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="radio-clinical-notes">Clinical Presentation & Symptoms</label>
                            <textarea id="radio-clinical-notes" rows="2" placeholder="e.g. 45 y/o male with high fever, productive cough, right pleuritic chest pain x 3 days."></textarea>
                        </div>

                        <div class="form-group">
                            <label>Diagnostic Scan Image (PNG, JPG, WEBP, DICOM)</label>
                            <div id="radio-dropzone" class="dropzone-container" onclick="document.getElementById('radio-file-input').click()">
                                <i class="fa-solid fa-cloud-arrow-up dropzone-icon"></i>
                                <h4>Drag and drop medical scan here, or browse files</h4>
                                <p class="text-muted" style="font-size:0.8rem; margin-top:4px;">Supports high-resolution PNG, JPG, WEBP, and DICOM</p>
                                <input type="file" id="radio-file-input" style="display:none;" accept="image/*,.dcm,.dicom">
                                
                                <div id="radio-preview-container" style="display:none;" class="dropzone-preview-wrapper">
                                    <img id="radio-preview-img" class="dropzone-preview-img" alt="Scan Preview">
                                    <p id="radio-file-name" style="font-size:0.8rem; font-weight:600; margin-top:6px;"></p>
                                </div>
                            </div>
                        </div>

                        <button type="submit" id="radio-submit-btn" class="btn btn-ai btn-block btn-lg">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Run AI Radiology Analysis
                        </button>
                    </form>
                </div>
            </div>

            <div id="radio-results-area">
                <div class="card" style="border-style:dashed; text-align:center; padding:50px 20px;">
                    <i class="fa-solid fa-microscope" style="font-size:2.5rem; color:#94a3b8; margin-bottom:12px;"></i>
                    <h4 style="color:var(--text-muted);">AI Analysis Awaiting Input</h4>
                    <p class="text-muted" style="font-size:0.85rem;">Upload an image or specify clinical findings to generate structured machine learning inferences.</p>
                </div>
            </div>
        </div>
    `;

    const fileInput = document.getElementById('radio-file-input');
    const dropzone = document.getElementById('radio-dropzone');
    const previewContainer = document.getElementById('radio-preview-container');
    const previewImg = document.getElementById('radio-preview-img');
    const fileName = document.getElementById('radio-file-name');

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileName.textContent = file.name;
            const reader = new FileReader();
            reader.onload = (re) => {
                previewImg.src = re.target.result;
                previewContainer.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            const file = e.dataTransfer.files[0];
            fileName.textContent = file.name;
            const reader = new FileReader();
            reader.onload = (re) => {
                previewImg.src = re.target.result;
                previewContainer.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });

    document.getElementById('ai-radiology-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('radio-submit-btn');
        const resultsArea = document.getElementById('radio-results-area');
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing Neural Diagnostic Model...`;
        resultsArea.innerHTML = `
            <div class="card card-glass text-center" style="padding:60px 20px;">
                <div class="spinner ai-pulse" style="margin:0 auto 16px;"></div>
                <h4>Analyzing Radiographic Features...</h4>
                <p class="text-muted" style="font-size:0.85rem;">Evaluating opacities, cardiothoracic contours, and bone integrity...</p>
            </div>
        `;

        try {
            const formData = new FormData();
            formData.append('patient_id', document.getElementById('radio-patient-id').value.trim());
            formData.append('modality', document.getElementById('radio-modality').value);
            formData.append('body_part', document.getElementById('radio-body-part').value);
            formData.append('clinical_notes', document.getElementById('radio-clinical-notes').value.trim());
            
            if (fileInput.files[0]) {
                formData.append('image', fileInput.files[0]);
            }

            const response = await window.API.analyzeRadiology(formData);
            state.currentAIRadiologyReport = response;
            renderRadiologyResults(resultsArea, response);
            showToast('AI Analysis Complete', 'Radiology report generated successfully.', 'success');
        } catch (err) {
            resultsArea.innerHTML = `
                <div class="card" style="border-color:#fca5a5; padding:30px;">
                    <h4 class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Analysis Failed</h4>
                    <p style="font-size:0.875rem;">${err.message}</p>
                </div>
            `;
            showToast('Analysis Error', err.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Run AI Radiology Analysis`;
        }
    });
}

function renderRadiologyResults(container, data) {
    const analysis = data.analysis;
    const reportId = data.report_id;
    const providerBadge = data.provider && data.provider !== 'mock'
        ? `<span class="badge status-badge-active" style="margin-left:8px;"><i class="fa-solid fa-bolt"></i> Live AI: ${data.provider.toUpperCase()} (${data.model || ''})</span>`
        : `<span class="badge" style="background:#fef3c7; color:#92400e; margin-left:8px;"><i class="fa-solid fa-robot"></i> Diagnostic Simulation (Fallback)</span>`;

    container.innerHTML = `
        <div class="ai-results-card">
            <div class="ai-results-header">
                <div>
                    <h3 style="color:white; margin:0; font-size:1.1rem;"><i class="fa-solid fa-x-ray"></i> ${analysis.modality} Analysis (${analysis.body_part})</h3>
                    <div style="margin-top:4px;">
                        <small style="opacity:0.8;">Report ID: #${reportId}</small>
                        ${providerBadge}
                    </div>
                </div>
                <div class="ai-confidence-badge">
                    Confidence: ${(analysis.confidence_score * 100).toFixed(0)}%
                </div>
            </div>

            <div class="ai-results-body">
                <div class="ai-safety-alert">
                    <i class="fa-solid fa-shield-heart" style="font-size:1.4rem;"></i>
                    <div>${analysis.safety_warning}</div>
                </div>

                <div class="ai-section-box" style="border-left:4px solid var(--primary); background:#f0fdfa;">
                    <h4><i class="fa-solid fa-bullseye"></i> Primary AI Diagnosis</h4>
                    <div style="font-size:1.1rem; font-weight:700; color:var(--secondary-dark); margin-bottom:4px;">
                        ${analysis.primary_diagnosis}
                    </div>
                </div>

                <div class="ai-section-box">
                    <h4><i class="fa-solid fa-magnifying-glass-chart"></i> Key Imaging Observations</h4>
                    <ul class="ai-findings-list">
                        ${analysis.key_findings.map(f => `<li>${f}</li>`).join('')}
                    </ul>
                </div>

                <div class="ai-section-box">
                    <h4><i class="fa-solid fa-code-compare"></i> Differential Diagnoses</h4>
                    ${analysis.differential_diagnoses.map(d => `
                        <div class="ai-differential-item">
                            <div>
                                <strong>${d.condition}</strong>
                                <div style="font-size:0.75rem; color:var(--text-muted);">${d.notes}</div>
                            </div>
                            <span class="badge ${d.probability === 'High' ? 'status-badge-inactive' : 'status-badge-active'}">${d.probability} Prob</span>
                        </div>
                    `).join('')}
                </div>

                <div class="ai-section-box">
                    <h4><i class="fa-solid fa-stethoscope"></i> Treatment & Clinical Recommendations</h4>
                    <ul class="ai-findings-list">
                        ${analysis.treatment_suggestions.map(t => `<li>${t}</li>`).join('')}
                    </ul>
                    <div style="margin-top:10px;">
                        <strong>Recommended Next Steps:</strong>
                        <ul class="ai-findings-list">
                            ${analysis.recommended_next_steps.map(n => `<li>${n}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <div class="ai-actions-footer">
                    <button class="btn btn-outline-danger" onclick="promptFlagAIReport(${reportId})">
                        <i class="fa-solid fa-flag"></i> Flag as Incorrect / Malicious
                    </button>
                    <button class="btn btn-primary" onclick="promptAcceptAIReport(${reportId})">
                        <i class="fa-solid fa-circle-check"></i> Accept AI Diagnosis
                    </button>
                </div>
            </div>
        </div>
    `;
}

// ------------------------------------------------------------
// TAB 2: AI LAB REPORT ANALYZER
// ------------------------------------------------------------
function renderLabTab(container) {
    container.innerHTML = `
        <div class="layout-grid">
            <div class="card card-glass">
                <div class="card-header">
                    <h3><i class="fa-solid fa-flask-vial"></i> Input Laboratory Parameters</h3>
                </div>
                <div class="card-body">
                    <form id="ai-lab-form">
                        <div class="form-row">
                            <div class="form-group col-6">
                                <label for="lab-patient-id">Associate with Patient ID (Optional)</label>
                                <input type="text" id="lab-patient-id" placeholder="e.g. PAT-0001">
                            </div>
                            <div class="form-group col-6">
                                <label for="lab-test-type">Test Category *</label>
                                <select id="lab-test-type" required>
                                    <option value="Comprehensive Blood Panel" selected>Comprehensive Blood Panel (CBC / Metabolic)</option>
                                    <option value="Lipid Profile & Glucose">Lipid Profile & Glucose / HbA1c</option>
                                    <option value="Urinalysis & Renal Function">Urinalysis & Renal Panel</option>
                                    <option value="Liver Function Test (LFT)">Liver Function Test (LFT)</option>
                                    <option value="Inflammatory Markers (CRP/ESR)">Inflammatory Markers (CRP / ESR)</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="lab-raw-text">Paste Lab Values or Formatted Pathology Text *</label>
                            <textarea id="lab-raw-text" rows="6" placeholder="Paste test printouts or parameters here, for example:
WBC: 13.8 (ref: 4.5 - 11.0)
CRP: 28.5 mg/L (ref: < 5.0)
Fasting Glucose: 142 mg/dL
HbA1c: 7.8%
Platelets: 280 (ref: 150-450)"></textarea>
                        </div>

                        <div class="form-group">
                            <label>Or Upload Laboratory PDF/Document Scan (Optional)</label>
                            <input type="file" id="lab-file-input" accept=".pdf,image/*">
                        </div>

                        <button type="submit" id="lab-submit-btn" class="btn btn-ai btn-block btn-lg">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Analyze Lab Parameters
                        </button>
                    </form>
                </div>
            </div>

            <div id="lab-results-area">
                <div class="card" style="border-style:dashed; text-align:center; padding:50px 20px;">
                    <i class="fa-solid fa-vial-circle-check" style="font-size:2.5rem; color:#94a3b8; margin-bottom:12px;"></i>
                    <h4 style="color:var(--text-muted);">Lab Interpreter Ready</h4>
                    <p class="text-muted" style="font-size:0.85rem;">Paste laboratory reports or select quick presets to parse out-of-range biomarkers automatically.</p>
                </div>
            </div>
        </div>
    `;

    document.getElementById('ai-lab-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('lab-submit-btn');
        const resultsArea = document.getElementById('lab-results-area');
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Parsing Biomarkers & Reference Ranges...`;
        resultsArea.innerHTML = `
            <div class="card card-glass text-center" style="padding:60px 20px;">
                <div class="spinner ai-pulse" style="margin:0 auto 16px;"></div>
                <h4>Evaluating Pathological Biomarkers...</h4>
                <p class="text-muted" style="font-size:0.85rem;">Checking normal limits, flagging critical values, and establishing etiologies...</p>
            </div>
        `;

        try {
            const formData = new FormData();
            formData.append('patient_id', document.getElementById('lab-patient-id').value.trim());
            formData.append('test_type', document.getElementById('lab-test-type').value);
            formData.append('raw_text', document.getElementById('lab-raw-text').value.trim());
            
            const fileInput = document.getElementById('lab-file-input');
            if (fileInput.files[0]) {
                formData.append('lab_file', fileInput.files[0]);
            }

            const response = await window.API.analyzeLabReport(formData);
            state.currentAILabReport = response;
            renderLabResults(resultsArea, response);
            showToast('AI Lab Analysis Complete', 'Pathology interpretation ready.', 'success');
        } catch (err) {
            resultsArea.innerHTML = `
                <div class="card" style="border-color:#fca5a5; padding:30px;">
                    <h4 class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Lab Analysis Failed</h4>
                    <p style="font-size:0.875rem;">${err.message}</p>
                </div>
            `;
            showToast('Analysis Error', err.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Analyze Lab Parameters`;
        }
    });
}

function renderLabResults(container, data) {
    const analysis = data.analysis;
    const reportId = data.report_id;
    const providerBadge = data.provider && data.provider !== 'mock'
        ? `<span class="badge status-badge-active" style="margin-left:8px;"><i class="fa-solid fa-bolt"></i> Live AI: ${data.provider.toUpperCase()}</span>`
        : `<span class="badge" style="background:#fef3c7; color:#92400e; margin-left:8px;"><i class="fa-solid fa-robot"></i> Diagnostic Simulation (Fallback)</span>`;

    container.innerHTML = `
        <div class="ai-results-card">
            <div class="ai-results-header">
                <div>
                    <h3 style="color:white; margin:0; font-size:1.1rem;"><i class="fa-solid fa-flask-vial"></i> ${analysis.test_type} Interpretation</h3>
                    <div style="margin-top:4px;">
                        <small style="opacity:0.8;">Report ID: #${reportId}</small>
                        ${providerBadge}
                    </div>
                </div>
            </div>

            <div class="ai-results-body">
                <div class="ai-safety-alert">
                    <i class="fa-solid fa-shield-heart" style="font-size:1.4rem;"></i>
                    <div>${analysis.safety_warning}</div>
                </div>

                <div class="ai-section-box">
                    <h4><i class="fa-solid fa-table-list"></i> Analyzed Biomarkers & Reference Ranges</h4>
                    <div class="table-responsive">
                        <table class="lab-table">
                            <thead>
                                <tr>
                                    <th>Parameter</th>
                                    <th>Observed Value</th>
                                    <th>Reference Range</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${analysis.parameters.map(p => {
                                    let statusClass = 'lab-val-normal';
                                    if (p.status === 'High') statusClass = 'lab-val-high';
                                    if (p.status === 'Low') statusClass = 'lab-val-low';
                                    return `
                                        <tr>
                                            <td><strong>${p.name}</strong></td>
                                            <td><span class="${statusClass}">${p.value} ${p.unit || ''}</span> ${p.critical ? '<span class="lab-critical-tag">CRITICAL</span>' : ''}</td>
                                            <td class="text-muted">${p.reference_range}</td>
                                            <td><span class="badge ${p.status === 'Normal' ? 'status-badge-active' : 'status-badge-inactive'}">${p.status}</span></td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="ai-section-box" style="border-left:4px solid var(--primary); background:#f0fdfa;">
                    <h4><i class="fa-solid fa-brain"></i> Clinical Interpretation</h4>
                    <p style="font-size:0.95rem; color:var(--secondary-dark); margin:0;">
                        ${analysis.primary_interpretation}
                    </p>
                </div>

                <div class="ai-section-box">
                    <h4><i class="fa-solid fa-list-check"></i> Potential Causes & Action Items</h4>
                    <strong>Potential Etiologies:</strong>
                    <ul class="ai-findings-list" style="margin-bottom:12px;">
                        ${analysis.potential_causes.map(c => `<li>${c}</li>`).join('')}
                    </ul>
                    <strong>Recommended Clinical Actions:</strong>
                    <ul class="ai-findings-list">
                        ${analysis.clinical_action_items.map(a => `<li>${a}</li>`).join('')}
                    </ul>
                </div>

                <div class="ai-actions-footer">
                    <button class="btn btn-outline-danger" onclick="promptFlagAIReport(${reportId})">
                        <i class="fa-solid fa-flag"></i> Flag as Incorrect
                    </button>
                    <button class="btn btn-primary" onclick="promptAcceptAIReport(${reportId})">
                        <i class="fa-solid fa-circle-check"></i> Accept & Save Lab Report
                    </button>
                </div>
            </div>
        </div>
    `;
}

// ------------------------------------------------------------
// TAB 3: AI DIAGNOSTIC HISTORY
// ------------------------------------------------------------
async function renderAIHistoryTab(container) {
    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h3><i class="fa-solid fa-clock-rotate-left"></i> Past AI Diagnoses & Verification Logs</h3>
                <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    <select id="ai-history-filter-type" style="width:160px; padding:6px 10px; font-size:0.85rem;" onchange="fetchAIHistory()">
                        <option value="">All Categories</option>
                        <option value="Radiology">Radiology</option>
                        <option value="Lab">Lab Reports</option>
                        <option value="Clinical_Assistant">Clinical Assistant</option>
                    </select>
                    <select id="ai-history-filter-status" style="width:140px; padding:6px 10px; font-size:0.85rem;" onchange="fetchAIHistory()">
                        <option value="">All Statuses</option>
                        <option value="Accepted">Accepted</option>
                        <option value="Flagged_Incorrect">Flagged</option>
                        <option value="Pending">Pending</option>
                    </select>
                    <button class="btn btn-outline-danger btn-sm" onclick="confirmClearAIHistory()"><i class="fa-solid fa-broom"></i> Clear AI History</button>
                </div>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Report ID</th>
                                <th>Type</th>
                                <th>Patient ID / Name</th>
                                <th>Specialist</th>
                                <th>Summary / Diagnosis</th>
                                <th>Status</th>
                                <th>Timestamp</th>
                                <th class="text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody id="ai-history-tbody">
                            <tr><td colspan="8" class="text-center"><div class="spinner-wrapper"><div class="spinner"></div></div></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    fetchAIHistory();
}

async function fetchAIHistory() {
    const tbody = document.getElementById('ai-history-tbody');
    if (!tbody) return;

    const typeFilter = document.getElementById('ai-history-filter-type')?.value || '';
    const statusFilter = document.getElementById('ai-history-filter-status')?.value || '';

    try {
        const rows = await window.API.getAIHistory({ type: typeFilter, status: statusFilter });
        state.aiHistoryList = rows;

        if (rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No past AI diagnostic reports found matching the filters.</td></tr>`;
            return;
        }

        tbody.innerHTML = rows.map(r => {
            let statusBadge = '<span class="badge status-badge-pending"><span class="dot"></span> Pending Review</span>';
            if (r.status === 'Accepted') {
                statusBadge = '<span class="badge status-badge-active"><span class="dot"></span> Accepted</span>';
            } else if (r.status === 'Flagged_Incorrect') {
                statusBadge = '<span class="badge status-badge-inactive"><span class="dot"></span> Flagged</span>';
            }

            const parsed = r.ai_output_parsed || {};
            const diagSummary = parsed.primary_diagnosis || parsed.primary_interpretation || parsed.clinical_summary || r.input_summary || '-';

            return `
                <tr>
                    <td><strong>#${r.id}</strong></td>
                    <td><span class="role-badge">${r.report_type}</span></td>
                    <td>${r.patient_id ? `<strong>${r.patient_id}</strong> (${r.patient_name || 'Record'})` : '<span class="text-muted">Unlinked</span>'}</td>
                    <td>${r.specialist_name || 'System'} <small class="text-muted">(${r.specialist_role || 'Staff'})</small></td>
                    <td><div style="max-width:260px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${diagSummary}</div></td>
                    <td>${statusBadge}</td>
                    <td class="text-muted" style="font-size:0.8rem;">${formatDate(r.created_at)}</td>
                    <td class="text-right">
                        ${r.status === 'Pending' ? `
                            <div style="display:inline-flex; gap:6px;">
                                <button class="btn btn-outline-success btn-sm" onclick="promptAcceptAIReport(${r.id})"><i class="fa-solid fa-check"></i></button>
                                <button class="btn btn-outline-danger btn-sm" onclick="promptFlagAIReport(${r.id})"><i class="fa-solid fa-flag"></i></button>
                            </div>
                        ` : `
                            <button class="btn btn-outline btn-sm" onclick="showHistoryDetailModal(${r.id})"><i class="fa-regular fa-eye"></i> Details</button>
                        `}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error: ${err.message}</td></tr>`;
    }
}

function showHistoryDetailModal(reportId) {
    const report = state.aiHistoryList.find(r => r.id === reportId);
    if (!report) return;

    openConfirmModal(`Report #${report.id} (${report.report_type}) - Status: ${report.status}\n\nClinical Feedback:\n${report.feedback_notes || 'No special feedback notes.'}`, () => {
        closeModal('confirm-modal');
    });
}

// ------------------------------------------------------------
// AI ACCEPT / FLAG PROMPTS
// ------------------------------------------------------------
function promptAcceptAIReport(reportId) {
    document.getElementById('ai-accept-report-id').value = reportId;
    document.getElementById('ai-accept-notes').value = '';
    openModal('ai-accept-modal');
}

function promptFlagAIReport(reportId) {
    document.getElementById('ai-flag-report-id').value = reportId;
    document.getElementById('ai-flag-reason').value = '';
    openModal('ai-flag-modal');
}

// ============================================================
// DOCTOR WORKSPACE: AI CLINICAL DECISION ASSISTANT
// ============================================================
async function runDoctorClinicalAI(patientId) {
    const aiContainer = document.getElementById('doctor-ai-panel-content');
    if (!aiContainer) return;

    aiContainer.innerHTML = `
        <div class="text-center" style="padding:20px;">
            <div class="spinner ai-pulse" style="margin:0 auto 10px;"></div>
            <p class="text-muted" style="font-size:0.85rem;">Synthesizing vitals, patient history, and clinical guidelines...</p>
        </div>
    `;

    try {
        const vitalsList = await window.API.getVitals(patientId);
        const latestVitals = vitalsList.length > 0 ? vitalsList[0] : {};

        const chiefComplaint = document.getElementById('diag-symptoms') ? document.getElementById('diag-symptoms').value : "Routine consultation";
        const clinicalData = {
            patient_id: patientId,
            vitals: latestVitals,
            chief_complaint: chiefComplaint,
            symptoms: chiefComplaint,
            medical_history: "No known adverse drug allergies.",
            current_medications: "None"
        };

        const res = await window.API.clinicalAssistant(clinicalData);
        state.currentAIClinicalReport = res;
        renderDoctorClinicalAISuggestions(aiContainer, res.suggestions, patientId, res.provider);
    } catch (err) {
        aiContainer.innerHTML = `<p class="text-danger" style="font-size:0.85rem;">AI Assistant Error: ${err.message}</p>`;
    }
}

function renderDoctorClinicalAISuggestions(container, data, patientId, provider) {
    const badge = provider && provider !== 'mock'
        ? `<span class="badge status-badge-active" style="margin-left:8px;"><i class="fa-solid fa-bolt"></i> Live AI: ${provider.toUpperCase()}</span>`
        : `<span class="badge" style="background:#fef3c7; color:#92400e; margin-left:8px;"><i class="fa-solid fa-robot"></i> Simulation (Fallback)</span>`;

    container.innerHTML = `
        <div class="ai-safety-alert" style="margin-bottom:14px; padding:10px;">
            <i class="fa-solid fa-triangle-exclamation" style="font-size:1.1rem;"></i>
            <span style="font-size:0.8rem;">${data.safety_warning}</span>
            ${badge}
        </div>

        <div style="margin-bottom:12px;">
            <h5 style="color:var(--secondary-dark); margin-bottom:6px;"><i class="fa-solid fa-stethoscope text-primary"></i> Top Diagnostic Hypotheses:</h5>
            ${data.potential_diagnoses.map(d => `
                <div style="background:white; padding:8px 12px; border:1px solid #cbd5e1; border-radius:4px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>${d.diagnosis}</strong> <span class="badge status-badge-active">${d.likelihood} Likelihood</span>
                        <div style="font-size:0.75rem; color:var(--text-muted);">${d.rationale}</div>
                    </div>
                    <button class="btn btn-outline btn-sm" onclick="applyAIDiagnosisToForm('${d.diagnosis.replace(/'/g, "\\'")}', '${d.rationale.replace(/'/g, "\\'")}')">
                        <i class="fa-solid fa-arrow-turn-down"></i> Apply
                    </button>
                </div>
            `).join('')}
        </div>

        <div>
            <h5 style="color:var(--secondary-dark); margin-bottom:6px;"><i class="fa-solid fa-pills text-primary"></i> Evidence-Based Suggested Regimen:</h5>
            ${data.suggested_treatment_plan.map(t => `
                <div style="background:white; padding:8px 12px; border:1px solid #cbd5e1; border-radius:4px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>${t.medication}</strong> - ${t.dosage} (${t.frequency} x ${t.duration})
                        <div style="font-size:0.75rem; color:#b45309;">⚠️ ${t.warning}</div>
                    </div>
                    <button class="btn btn-outline btn-sm" onclick="applyAIPrescriptionToForm('${t.medication.replace(/'/g, "\\'")}', '${t.dosage}', '${t.frequency}', '${t.duration}', '${t.warning.replace(/'/g, "\\'")}')">
                        <i class="fa-solid fa-arrow-turn-down"></i> Apply
                    </button>
                </div>
            `).join('')}
        </div>
    `;
}

function applyAIDiagnosisToForm(diagText, notes) {
    const diagInput = document.getElementById('diag-text');
    const notesInput = document.getElementById('diag-notes');
    if (diagInput) diagInput.value = diagText;
    if (notesInput) notesInput.value = `[AI Supported] ${notes}`;
    showToast('Applied to Form', `Diagnosis "${diagText}" loaded into form.`, 'success');
}

function applyAIPrescriptionToForm(med, dosage, freq, duration, notes) {
    showAddPrescriptionForm(state.activePatient ? state.activePatient.patient_id : '');
    setTimeout(() => {
        if (document.getElementById('presc-medication')) document.getElementById('presc-medication').value = med;
        if (document.getElementById('presc-dosage')) document.getElementById('presc-dosage').value = dosage;
        if (document.getElementById('presc-frequency')) document.getElementById('presc-frequency').value = freq;
        if (document.getElementById('presc-duration')) document.getElementById('presc-duration').value = duration;
        if (document.getElementById('presc-notes')) document.getElementById('presc-notes').value = `[AI Pre-filled] ${notes}`;
    }, 100);
    showToast('Applied to Prescription', `${med} pre-filled into prescription modal.`, 'success');
}

// ============================================================
// VIEW 3: ADMIN USER MANAGEMENT
// ============================================================
async function renderUsersView() {
    const container = document.getElementById('page-content');
    
    container.innerHTML = `
        <div class="dashboard-title-row">
            <h2>Staff User Accounts</h2>
            <button class="btn btn-primary" onclick="showCreateUserForm()">
                <i class="fa-solid fa-user-plus"></i> Add New Staff Member
            </button>
        </div>
        
        <div class="card">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table" id="users-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Full Name</th>
                                <th>Role</th>
                                <th>Created At</th>
                                <th>Status</th>
                                <th class="text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="users-table-body">
                            <tr><td colspan="7" class="text-center"><div class="spinner-wrapper"><div class="spinner"></div></div></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    try {
        const users = await window.API.getUsers();
        state.users = users;
        
        const tbody = document.getElementById('users-table-body');
        if (users.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No staff accounts registered.</td></tr>`;
            return;
        }
        
        tbody.innerHTML = users.map(user => {
            const statusBadge = user.status 
                ? `<span class="badge status-badge-active"><span class="dot"></span> Active</span>`
                : `<span class="badge status-badge-inactive"><span class="dot"></span> Disabled</span>`;
                
            const toggleIcon = user.status ? 'fa-solid fa-user-slash' : 'fa-solid fa-user-check';
            const toggleText = user.status ? 'Disable' : 'Enable';
            const toggleBtnClass = user.status ? 'btn-outline' : 'btn-primary';
            const isSelf = user.id === state.user.id;
            
            return `
                <tr>
                    <td>${user.id}</td>
                    <td><strong>${user.username}</strong></td>
                    <td>${user.full_name}</td>
                    <td><span class="role-badge">${user.role}</span></td>
                    <td class="text-muted">${formatDate(user.created_at)}</td>
                    <td>${statusBadge}</td>
                    <td class="text-right">
                        <div style="display:inline-flex; gap:6px;">
                            <button class="btn btn-outline btn-sm" onclick="showEditUserForm(${user.id})">
                                <i class="fa-regular fa-pen-to-square"></i> Edit
                            </button>
                            <button class="btn ${toggleBtnClass} btn-sm" ${isSelf ? 'disabled title="You cannot disable yourself"' : ''} onclick="toggleUserStatus(${user.id})">
                                <i class="${toggleIcon}"></i> ${toggleText}
                            </button>
                            <button class="btn btn-danger btn-sm" ${isSelf ? 'disabled title="You cannot delete yourself"' : ''} onclick="confirmDeleteUser(${user.id}, '${escapeHtml(user.username)}')">
                                <i class="fa-solid fa-trash"></i> Delete
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
    } catch (err) {
        showToast('Load Failed', 'Could not retrieve staff accounts list.', 'error');
    }
}

// ============================================================
// VIEW 4: SYSTEM ACTIVITY LOGS
// ============================================================
async function renderLogsView() {
    const container = document.getElementById('page-content');
    
    container.innerHTML = `
        <div class="dashboard-title-row">
            <h2>System Activity & Dual Audit Trail</h2>
            <button class="btn btn-danger" onclick="confirmClearLogs()"><i class="fa-solid fa-broom"></i> Clear Logs (DB & Physical Files)</button>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h3><i class="fa-solid fa-clock-rotate-left"></i> Persistent Activity Logs (MySQL & /logs/audit.log)</h3>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Timestamp</th>
                                <th>User</th>
                                <th>Role</th>
                                <th>Action</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody id="logs-table-body">
                            <tr><td colspan="6" class="text-center"><div class="spinner-wrapper"><div class="spinner"></div></div></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    try {
        const logs = await window.API.getLogs();
        const tbody = document.getElementById('logs-table-body');
        
        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No activity logs recorded.</td></tr>`;
            return;
        }
        
        tbody.innerHTML = logs.map(log => `
            <tr>
                <td class="text-muted">${log.id}</td>
                <td class="text-muted">${formatDate(log.created_at)}</td>
                <td><strong>${log.username || 'System'}</strong></td>
                <td><span class="role-badge">${log.role || 'System'}</span></td>
                <td><strong>${log.action}</strong></td>
                <td>${log.details || ''}</td>
            </tr>
        `).join('');
    } catch (err) {
        showToast('Load Failed', 'Could not retrieve system activity logs.', 'error');
    }
}

// ============================================================
// VIEW 5: PATIENTS REGISTRY & CARE
// ============================================================
async function renderPatientsView() {
    const container = document.getElementById('page-content');
    const role = state.user.role;
    
    const showRegisterBtn = ['Receptionist', 'Admin'].includes(role)
        ? `<button class="btn btn-primary" onclick="showRegisterPatientForm()"><i class="fa-solid fa-user-plus"></i> Register Patient</button>`
        : '';
        
    container.innerHTML = `
        <div class="dashboard-title-row">
            <h2>Patient Registry</h2>
            ${showRegisterBtn}
        </div>
        
        <div class="card">
            <div class="card-body">
                <div class="table-actions-bar">
                    <div class="search-input-wrapper">
                        <i class="fa-solid fa-magnifying-glass search-icon"></i>
                        <input type="text" id="patient-search-input" value="${state.patientsSearch}" placeholder="Search ID, name, phone...">
                    </div>
                </div>
                
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th class="sortable" data-sort="patient_id">Patient ID ${getSortIcon('patient_id')}</th>
                                <th class="sortable" data-sort="full_name">Full Name ${getSortIcon('full_name')}</th>
                                <th class="sortable" data-sort="dob">DOB ${getSortIcon('dob')}</th>
                                <th>Gender</th>
                                <th>Phone</th>
                                <th class="sortable" data-sort="created_at">Registered At ${getSortIcon('created_at')}</th>
                                <th class="text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="patients-table-body">
                            <tr><td colspan="7" class="text-center"><div class="spinner-wrapper"><div class="spinner"></div></div></td></tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="pagination">
                    <span id="pagination-info" class="text-muted" style="font-size:0.875rem;">Showing 0 to 0 of 0 patients</span>
                    <div class="pagination-buttons">
                        <button id="btn-prev-page" class="btn btn-outline btn-sm"><i class="fa-solid fa-chevron-left"></i> Previous</button>
                        <button id="btn-next-page" class="btn btn-outline btn-sm">Next <i class="fa-solid fa-chevron-right"></i></button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.querySelectorAll('th.sortable').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', (e) => {
            const field = e.currentTarget.getAttribute('data-sort');
            if (state.patientsSort === field) {
                state.patientsOrder = state.patientsOrder === 'asc' ? 'desc' : 'asc';
            } else {
                state.patientsSort = field;
                state.patientsOrder = 'asc';
            }
            fetchAndRenderPatients();
        });
    });
    
    const searchInput = document.getElementById('patient-search-input');
    searchInput.addEventListener('input', debounce((e) => {
        state.patientsSearch = e.target.value.trim();
        state.patientsPage = 1;
        fetchAndRenderPatients();
    }, 400));
    
    document.getElementById('btn-prev-page').addEventListener('click', () => {
        if (state.patientsPage > 1) {
            state.patientsPage--;
            fetchAndRenderPatients();
        }
    });
    document.getElementById('btn-next-page').addEventListener('click', () => {
        const maxPage = Math.ceil(state.patientsTotal / state.patientsLimit);
        if (state.patientsPage < maxPage) {
            state.patientsPage++;
            fetchAndRenderPatients();
        }
    });
    
    fetchAndRenderPatients();
}

async function fetchAndRenderPatients() {
    const tbody = document.getElementById('patients-table-body');
    if (!tbody) return;
    
    try {
        const response = await window.API.getPatients({
            search: state.patientsSearch,
            sort: state.patientsSort,
            order: state.patientsOrder,
            page: state.patientsPage,
            limit: state.patientsLimit
        });
        
        state.patients = response.patients;
        state.patientsTotal = response.total;
        
        const start = state.patientsTotal === 0 ? 0 : (state.patientsPage - 1) * state.patientsLimit + 1;
        const end = Math.min(state.patientsPage * state.patientsLimit, state.patientsTotal);
        document.getElementById('pagination-info').textContent = `Showing ${start} to ${end} of ${state.patientsTotal} patients`;
        
        document.getElementById('btn-prev-page').disabled = state.patientsPage === 1;
        document.getElementById('btn-next-page').disabled = end >= state.patientsTotal;
        
        if (state.patients.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No patient records found.</td></tr>`;
            return;
        }
        
        const role = state.user.role;
        tbody.innerHTML = state.patients.map(p => {
            let actionBtn = '';
            if (['Receptionist', 'Admin'].includes(role)) {
                actionBtn = `
                    <div style="display:inline-flex; gap:6px;">
                        <button class="btn btn-outline btn-sm" onclick="showEditPatientForm('${p.patient_id}')">
                            <i class="fa-regular fa-pen-to-square"></i> Edit
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="viewPatientProfile('${p.patient_id}')">
                            <i class="fa-solid fa-hospital-user"></i> Profile
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="confirmDeletePatient('${p.patient_id}', '${escapeHtml(p.full_name)}')">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </div>
                `;
            } else if (['Doctor', 'Admin'].includes(role)) {
                actionBtn = `
                    <button class="btn btn-secondary btn-sm" onclick="viewPatientProfile('${p.patient_id}')">
                        <i class="fa-solid fa-stethoscope"></i> Consult Patient
                    </button>
                `;
            } else if (role === 'Nurse') {
                actionBtn = `
                    <button class="btn btn-primary btn-sm" onclick="viewPatientProfile('${p.patient_id}')">
                        <i class="fa-solid fa-heart-pulse"></i> Patient Vitals
                    </button>
                `;
            }
            
            return `
                <tr>
                    <td><span class="role-badge">${p.patient_id}</span></td>
                    <td><strong>${p.full_name}</strong></td>
                    <td>${p.dob}</td>
                    <td>${p.gender}</td>
                    <td>${p.phone}</td>
                    <td class="text-muted">${formatDate(p.created_at)}</td>
                    <td class="text-right">${actionBtn}</td>
                </tr>
            `;
        }).join('');
        
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error loading patients: ${err.message}</td></tr>`;
    }
}

function getSortIcon(field) {
    if (state.patientsSort !== field) return '<i class="fa-solid fa-sort text-muted" style="font-size:0.75rem; margin-left:4px;"></i>';
    return state.patientsOrder === 'asc' 
        ? '<i class="fa-solid fa-sort-up text-primary" style="font-size:0.75rem; margin-left:4px;"></i>' 
        : '<i class="fa-solid fa-sort-down text-primary" style="font-size:0.75rem; margin-left:4px;"></i>';
}

// ============================================================
// PROFILE: PATIENT COMPLETE RECORD DETAILS (RBAC CHECKED)
// ============================================================
async function viewPatientProfile(patientId) {
    const container = document.getElementById('page-content');
    const role = state.user.role;
    
    container.innerHTML = `<div class="spinner-wrapper"><div class="spinner"></div></div>`;
    
    try {
        const patient = await window.API.getPatient(patientId);
        state.activePatient = patient;
        
        let actionsRow = '';
        if (['Receptionist', 'Admin'].includes(role)) {
            actionsRow = `
                <div style="display:inline-flex; gap:10px; flex-wrap:wrap;">
                    <button class="btn btn-outline" onclick="showEditPatientForm('${patient.patient_id}')"><i class="fa-regular fa-pen-to-square"></i> Edit Info</button>
                    <button class="btn btn-outline-danger" onclick="confirmClearPatientHistory('${patient.patient_id}', '${escapeHtml(patient.full_name)}')"><i class="fa-solid fa-broom"></i> Clear Patient History</button>
                    <button class="btn btn-danger" onclick="confirmDeletePatient('${patient.patient_id}', '${escapeHtml(patient.full_name)}')"><i class="fa-solid fa-trash"></i> Delete Patient</button>
                </div>
            `;
        } else if (['Doctor', 'Admin'].includes(role)) {
            actionsRow = `
                <div style="display:inline-flex; gap:10px; flex-wrap:wrap;">
                    <button class="btn btn-ai" onclick="runDoctorClinicalAI('${patient.patient_id}')"><i class="fa-solid fa-wand-magic-sparkles"></i> AI Clinical Assistant</button>
                    <button class="btn btn-primary" onclick="showAddDiagnosisForm('${patient.patient_id}')"><i class="fa-solid fa-stethoscope"></i> Log Diagnosis</button>
                    <button class="btn btn-secondary" onclick="showAddPrescriptionForm('${patient.patient_id}')"><i class="fa-solid fa-prescription-bottle-medical"></i> Prescribe</button>
                    <button class="btn btn-outline" onclick="showAddVitalsForm('${patient.patient_id}')"><i class="fa-solid fa-heart-pulse"></i> Log Vitals</button>
                    <button class="btn btn-outline-danger" onclick="confirmClearPatientHistory('${patient.patient_id}', '${escapeHtml(patient.full_name)}')"><i class="fa-solid fa-broom"></i> Clear History</button>
                </div>
            `;
        } else if (role === 'Nurse') {
            actionsRow = `
                <div style="display:inline-flex; gap:10px; flex-wrap:wrap;">
                    <button class="btn btn-primary" onclick="showAddVitalsForm('${patient.patient_id}')"><i class="fa-solid fa-heart-pulse"></i> Record New Vitals</button>
                    <button class="btn btn-outline-danger" onclick="confirmClearVitals('${patient.patient_id}')"><i class="fa-solid fa-broom"></i> Clear Vitals History</button>
                </div>
            `;
        }
        
        const summaryCard = `
            <div class="profile-summary-card">
                <div style="width:100%;">
                    <div class="patient-info-name">
                        <h3>${patient.full_name}</h3>
                        <span class="role-badge" style="font-size:0.875rem;">${patient.patient_id}</span>
                    </div>
                    <div class="patient-meta-grid">
                        <div><strong>DOB:</strong> ${patient.dob}</div>
                        <div><strong>Gender:</strong> ${patient.gender}</div>
                        <div><strong>Phone:</strong> ${patient.phone}</div>
                        <div><strong>Email:</strong> ${patient.email || 'N/A'}</div>
                    </div>
                    <div class="patient-meta-grid" style="margin-top:10px; padding-top:10px; border-top:1px solid #f1f5f9;">
                        <div><strong>Emergency Contact:</strong> ${patient.emergency_contact_name} (${patient.emergency_contact_relation})</div>
                        <div><strong>EC Phone:</strong> ${patient.emergency_contact_phone}</div>
                        <div style="grid-column: span 2;"><strong>Residential Address:</strong> ${patient.address || 'None'}</div>
                    </div>
                </div>
            </div>
        `;
        
        let lowerSections = '';
        
        if (role === 'Receptionist') {
            lowerSections = `
                <div class="card">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-circle-info"></i> Patient Registry Metadata</h3>
                    </div>
                    <div class="card-body">
                        <p><strong>Registered:</strong> ${formatDate(patient.created_at)}</p>
                        <p><strong>Last Updated:</strong> ${formatDate(patient.updated_at)}</p>
                    </div>
                </div>
            `;
        } else if (role === 'Nurse') {
            lowerSections = `
                <div class="layout-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-heart-pulse"></i> Patient Vitals Logs</h3>
                        </div>
                        <div class="card-body" id="profile-vitals-container">
                            <div class="spinner-wrapper"><div class="spinner"></div></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-shield-halved"></i> Access Restriction</h3>
                        </div>
                        <div class="card-body">
                            <p style="font-size:0.875rem; color:var(--text-muted);">
                                <i class="fa-solid fa-lock text-danger"></i>
                                Clinical records (prescriptions, physician diagnoses) are locked for non-prescribing staff.
                            </p>
                        </div>
                    </div>
                </div>
            `;
            setTimeout(() => loadVitalsHistory(patient.patient_id), 50);
        } else if (['Doctor', 'Admin'].includes(role)) {
            lowerSections = `
                <div class="clinical-ai-panel">
                    <div class="clinical-ai-header">
                        <h3><i class="fa-solid fa-wand-magic-sparkles"></i> AI Clinical Decision Assistant</h3>
                        <button class="btn btn-ai btn-sm" onclick="runDoctorClinicalAI('${patient.patient_id}')"><i class="fa-solid fa-rotate"></i> Re-Analyze Case</button>
                    </div>
                    <div id="doctor-ai-panel-content">
                        <p style="font-size:0.85rem; color:#0f766e; margin:0;">Click "AI Clinical Assistant" or "Re-Analyze Case" to generate evidence-based diagnostic recommendations, drug-drug interaction alerts, and pre-fill regimens.</p>
                    </div>
                </div>

                <div class="layout-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-notes-medical"></i> Clinical History (Diagnoses & Prescriptions)</h3>
                        </div>
                        <div class="card-body" id="profile-clinical-container">
                            <div class="spinner-wrapper"><div class="spinner"></div></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fa-solid fa-heart-pulse"></i> Patient Vitals Logs</h3>
                        </div>
                        <div class="card-body" id="profile-vitals-container">
                            <div class="spinner-wrapper"><div class="spinner"></div></div>
                        </div>
                    </div>
                </div>
            `;
            setTimeout(() => {
                loadClinicalHistory(patient.patient_id);
                loadVitalsHistory(patient.patient_id);
            }, 50);
        }
        
        container.innerHTML = `
            <div class="dashboard-title-row">
                <div style="display:flex; align-items:center; gap:12px;">
                    <button class="btn btn-outline" onclick="navigateTo('patients')"><i class="fa-solid fa-arrow-left"></i> Back</button>
                    <h2 style="margin:0;">Patient Case File</h2>
                </div>
                ${actionsRow}
            </div>
            ${summaryCard}
            ${lowerSections}
        `;
        
    } catch (err) {
        showToast('Error', err.message, 'error');
        navigateTo('patients');
    }
}

async function loadVitalsHistory(patientId) {
    const el = document.getElementById('profile-vitals-container');
    if (!el) return;
    
    try {
        const vitals = await window.API.getVitals(patientId);
        
        if (vitals.length === 0) {
            el.innerHTML = `
                <div class="text-center text-muted" style="padding:30px;">
                    <i class="fa-solid fa-heart-pulse" style="font-size:2rem; margin-bottom:10px;"></i>
                    <p>No vitals records logged for this patient yet.</p>
                </div>
            `;
            return;
        }
        
        el.innerHTML = `
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>BP (mmHg)</th>
                            <th>Temp (°C)</th>
                            <th>Pulse (BPM)</th>
                            <th>Weight/Height</th>
                            <th>Recorded By</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${vitals.map(v => {
                            const bp = (v.bp_systolic && v.bp_diastolic) ? `${v.bp_systolic}/${v.bp_diastolic}` : 'N/A';
                            const temp = v.temperature ? `${v.temperature}°C` : 'N/A';
                            const pulse = v.pulse_rate ? `${v.pulse_rate}` : 'N/A';
                            const stats = (v.weight && v.height) ? `${v.weight}kg / ${v.height}cm` : 'N/A';
                            
                            return `
                                <tr>
                                    <td class="text-muted" style="font-size:0.8rem;">${formatDate(v.created_at)}</td>
                                    <td><strong>${bp}</strong></td>
                                    <td>${temp}</td>
                                    <td>${pulse}</td>
                                    <td>${stats}</td>
                                    <td>${v.recorder_name} <span class="role-badge" style="font-size:0.65rem;">${v.recorder_role}</span></td>
                                    <td><small>${v.nursing_notes || '-'}</small></td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        el.innerHTML = `<p class="text-danger">Failed to load vitals: ${err.message}</p>`;
    }
}

async function loadClinicalHistory(patientId) {
    const el = document.getElementById('profile-clinical-container');
    if (!el) return;
    
    try {
        const clinical = await window.API.getClinicalRecords(patientId);
        
        let diagHtml = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h4 style="margin:0; color:var(--secondary-dark);">Diagnoses</h4>
                ${clinical.diagnoses.length > 0 ? `<button class="btn btn-outline-danger btn-sm" onclick="confirmClearDiagnoses('${patientId}')"><i class="fa-solid fa-broom"></i> Clear Diagnoses</button>` : ''}
            </div>
        `;
        if (clinical.diagnoses.length === 0) {
            diagHtml += '<p class="text-muted" style="font-size:0.875rem; margin-bottom:20px;">No diagnoses recorded.</p>';
        } else {
            diagHtml += clinical.diagnoses.map(d => `
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid var(--primary); padding:12px; border-radius:4px; margin-bottom:10px; position:relative;">
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">
                        <span>By ${d.doctor_name}</span>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>${formatDate(d.created_at)}</span>
                            <button class="btn btn-outline-danger btn-xs" style="padding:2px 6px; font-size:0.75rem;" title="Delete diagnosis" onclick="confirmDeleteDiagnosis(${d.id}, '${patientId}')">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div style="font-weight:700; color:var(--secondary-dark);">${d.diagnosis_text}</div>
                    <div style="font-size:0.85rem; margin-top:4px;"><strong>Symptoms:</strong> ${d.symptoms || 'None'}</div>
                    ${d.notes ? `<div style="font-size:0.85rem; color:var(--text-muted); margin-top:2px;"><strong>Notes:</strong> ${d.notes}</div>` : ''}
                </div>
            `).join('') + '<div style="margin-bottom:20px;"></div>';
        }
        
        let prescHtml = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h4 style="margin:0; color:var(--secondary-dark);">Active Prescriptions</h4>
                ${clinical.prescriptions.length > 0 ? `<button class="btn btn-outline-danger btn-sm" onclick="confirmClearPrescriptions('${patientId}')"><i class="fa-solid fa-broom"></i> Clear Prescriptions</button>` : ''}
            </div>
        `;
        if (clinical.prescriptions.length === 0) {
            prescHtml += '<p class="text-muted" style="font-size:0.875rem;">No prescriptions issued.</p>';
        } else {
            prescHtml += clinical.prescriptions.map(p => `
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid var(--secondary); padding:12px; border-radius:4px; margin-bottom:10px; position:relative;">
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">
                        <span>By ${p.doctor_name}</span>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>${formatDate(p.created_at)}</span>
                            <button class="btn btn-outline-danger btn-xs" style="padding:2px 6px; font-size:0.75rem;" title="Remove prescription" onclick="confirmDeletePrescription(${p.id}, '${patientId}')">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div style="font-weight:700; color:var(--secondary);"><i class="fa-solid fa-pills"></i> ${p.medication}</div>
                    <div style="font-size:0.85rem; margin-top:4px;">
                        <span>${p.dosage} | ${p.frequency} | ${p.duration}</span>
                    </div>
                    ${p.notes ? `<div style="font-size:0.85rem; color:var(--text-muted); margin-top:2px;"><strong>Usage:</strong> ${p.notes}</div>` : ''}
                </div>
            `).join('');
        }
        
        el.innerHTML = diagHtml + prescHtml;
    } catch (err) {
        el.innerHTML = `<p class="text-danger">Failed to load clinical records: ${err.message}</p>`;
    }
}

// ============================================================
// FORM DIALOG EVENTS & INITIATIONS
// ============================================================
function showCreateUserForm() {
    document.getElementById('user-modal-title').textContent = 'Create New User Account';
    document.getElementById('user-form-id').value = '';
    document.getElementById('user-username').value = '';
    document.getElementById('user-username').disabled = false;
    document.getElementById('user-fullname').value = '';
    document.getElementById('user-role').value = '';
    document.getElementById('user-password').value = '';
    document.getElementById('user-password-label').textContent = 'Password *';
    document.getElementById('user-password').required = true;
    document.getElementById('user-password-help').style.display = 'none';
    openModal('user-modal');
}

function showEditUserForm(userId) {
    const user = state.users.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('user-modal-title').textContent = `Edit User: ${user.username}`;
    document.getElementById('user-form-id').value = user.id;
    document.getElementById('user-username').value = user.username;
    document.getElementById('user-username').disabled = true;
    document.getElementById('user-fullname').value = user.full_name;
    document.getElementById('user-role').value = user.role;
    document.getElementById('user-password').value = '';
    document.getElementById('user-password-label').textContent = 'Password (Update)';
    document.getElementById('user-password').required = false;
    document.getElementById('user-password-help').style.display = 'block';
    openModal('user-modal');
}

async function toggleUserStatus(userId) {
    const user = state.users.find(u => u.id === userId);
    if (!user) return;
    
    const actionText = user.status ? 'DISABLE' : 'ENABLE';
    openConfirmModal(`Are you sure you want to ${actionText} the staff account for "${user.full_name}"?`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.toggleUserStatus(userId);
            showToast('Status Updated', res.message, 'success');
            renderUsersView();
        } catch (err) {
            showToast('Action Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function showRegisterPatientForm() {
    document.getElementById('patient-modal-title').textContent = 'Register New Patient';
    document.getElementById('patient-form-id').value = '';
    document.getElementById('patient-form').reset();
    openModal('patient-modal');
}

function showEditPatientForm(patientId) {
    const p = state.patients.find(x => x.patient_id === patientId) || state.activePatient;
    if (!p) return;
    
    document.getElementById('patient-modal-title').textContent = `Edit Patient Profile: ${p.patient_id}`;
    document.getElementById('patient-form-id').value = p.patient_id;
    document.getElementById('patient-fullname').value = p.full_name;
    document.getElementById('patient-dob').value = p.dob;
    document.getElementById('patient-gender').value = p.gender;
    document.getElementById('patient-phone').value = p.phone;
    document.getElementById('patient-email').value = p.email || '';
    document.getElementById('patient-address').value = p.address || '';
    document.getElementById('patient-ec-name').value = p.emergency_contact_name;
    document.getElementById('patient-ec-phone').value = p.emergency_contact_phone;
    document.getElementById('patient-ec-relation').value = p.emergency_contact_relation;
    
    openModal('patient-modal');
}

function showAddDiagnosisForm(patientId) {
    document.getElementById('diagnosis-patient-id').value = patientId;
    document.getElementById('diagnosis-form').reset();
    openModal('diagnosis-modal');
}

function showAddPrescriptionForm(patientId) {
    document.getElementById('prescription-patient-id').value = patientId;
    document.getElementById('prescription-form').reset();
    openModal('prescription-modal');
}

function showAddVitalsForm(patientId) {
    document.getElementById('vitals-patient-id').value = patientId;
    document.getElementById('vitals-form').reset();
    openModal('vitals-modal');
}

// ============================================================
// EVENT LISTENERS & SUBMISSIONS
// ============================================================
function initEventListeners() {
    document.getElementById('mobile-toggle').addEventListener('click', () => {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('sidebar-open');
        document.body.classList.toggle('sidebar-overlay-active');
    });

    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });

    document.querySelectorAll('[data-close]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modalId = e.currentTarget.getAttribute('data-close');
            closeModal(modalId);
        });
    });

    // Login Form Submit
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const usernameInput = document.getElementById('login-username').value.trim();
        const passwordInput = document.getElementById('login-password').value;
        const btn = document.getElementById('login-btn');

        if (!usernameInput || !passwordInput) {
            showToast('Input Error', 'Please enter username and password.', 'warning');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...`;

        try {
            const data = await window.API.login(usernameInput, passwordInput);
            setupUserSession(data.user);
        } catch (err) {
            showToast('Login Failed', err.message, 'error');
            btn.disabled = false;
            btn.innerHTML = `<span>Sign In</span> <i class="fa-solid fa-arrow-right"></i>`;
        }
    });

    // Logout Button
    document.getElementById('logout-btn').addEventListener('click', () => {
        openConfirmModal('Are you sure you want to sign out?', async () => {
            closeModal('confirm-modal');
            showAppLoader();
            try {
                await window.API.logout();
                showToast('Signed Out', 'You have been logged out successfully.', 'info');
                showLoginScreen();
            } catch (err) {
                showLoginScreen();
            } finally {
                hideAppLoader();
            }
        });
    });

    // Admin: Save User Form Submit
    document.getElementById('user-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const userId = document.getElementById('user-form-id').value;
        const username = document.getElementById('user-username').value.trim();
        const fullname = document.getElementById('user-fullname').value.trim();
        const role = document.getElementById('user-role').value;
        const password = document.getElementById('user-password').value;

        showAppLoader();
        try {
            if (userId) {
                const res = await window.API.updateUser(userId, { full_name: fullname, role, password });
                showToast('Success', res.message, 'success');
            } else {
                const res = await window.API.createUser({ username, full_name: fullname, role, password });
                showToast('Success', res.message, 'success');
            }
            closeModal('user-modal');
            renderUsersView();
        } catch (err) {
            showToast('Save Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });

    // Receptionist: Save Patient Form Submit
    document.getElementById('patient-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const patientId = document.getElementById('patient-form-id').value;
        const fullname = document.getElementById('patient-fullname').value.trim();
        const dob = document.getElementById('patient-dob').value;
        const gender = document.getElementById('patient-gender').value;
        const phone = document.getElementById('patient-phone').value.trim();
        const email = document.getElementById('patient-email').value.trim();
        const address = document.getElementById('patient-address').value.trim();
        const ecName = document.getElementById('patient-ec-name').value.trim();
        const ecPhone = document.getElementById('patient-ec-phone').value.trim();
        const ecRelation = document.getElementById('patient-ec-relation').value.trim();

        if (!fullname || !dob || !gender || !phone || !ecName || !ecPhone || !ecRelation) {
            showToast('Input Validation', 'Please fill out all required fields marked with *', 'warning');
            return;
        }

        showAppLoader();
        try {
            const patientData = {
                full_name: fullname, dob, gender, phone, email, address,
                emergency_contact_name: ecName, emergency_contact_phone: ecPhone, emergency_contact_relation: ecRelation
            };

            if (patientId) {
                const res = await window.API.updatePatient(patientId, patientData);
                showToast('Success', res.message, 'success');
            } else {
                const res = await window.API.registerPatient(patientData);
                showToast('Success', res.message, 'success');
            }
            
            closeModal('patient-modal');
            
            if (state.activePage === 'patients') {
                fetchAndRenderPatients();
            } else {
                navigateTo('patients');
            }
        } catch (err) {
            showToast('Registration Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });

    // Doctor: Save Diagnosis Form Submit
    document.getElementById('diagnosis-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const patientId = document.getElementById('diagnosis-patient-id').value;
        const symptoms = document.getElementById('diag-symptoms').value.trim();
        const text = document.getElementById('diag-text').value.trim();
        const notes = document.getElementById('diag-notes').value.trim();

        if (!text) {
            showToast('Validation Error', 'Diagnosis field is required.', 'warning');
            return;
        }

        showAppLoader();
        try {
            const res = await window.API.addDiagnosis(patientId, { symptoms, diagnosis_text: text, notes });
            showToast('Success', res.message, 'success');
            closeModal('diagnosis-modal');
            viewPatientProfile(patientId);
        } catch (err) {
            showToast('Save Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });

    // Doctor: Save Prescription Form Submit
    document.getElementById('prescription-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const patientId = document.getElementById('prescription-patient-id').value;
        const medication = document.getElementById('presc-medication').value.trim();
        const dosage = document.getElementById('presc-dosage').value.trim();
        const frequency = document.getElementById('presc-frequency').value.trim();
        const duration = document.getElementById('presc-duration').value.trim();
        const notes = document.getElementById('presc-notes').value.trim();

        if (!medication || !dosage || !frequency || !duration) {
            showToast('Validation Error', 'Please complete all required prescription fields.', 'warning');
            return;
        }

        showAppLoader();
        try {
            const res = await window.API.addPrescription(patientId, { medication, dosage, frequency, duration, notes });
            showToast('Success', res.message, 'success');
            closeModal('prescription-modal');
            viewPatientProfile(patientId);
        } catch (err) {
            showToast('Save Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });

    // Nurse/Doctor: Save Vitals Form Submit
    document.getElementById('vitals-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const patientId = document.getElementById('vitals-patient-id').value;
        const systolic = document.getElementById('vitals-systolic').value;
        const diastolic = document.getElementById('vitals-diastolic').value;
        const temp = document.getElementById('vitals-temp').value;
        const pulse = document.getElementById('vitals-pulse').value;
        const weight = document.getElementById('vitals-weight').value;
        const height = document.getElementById('vitals-height').value;
        const notes = document.getElementById('vitals-notes').value.trim();

        showAppLoader();
        try {
            const res = await window.API.addVitals(patientId, {
                bp_systolic: systolic,
                bp_diastolic: diastolic,
                temperature: temp,
                pulse_rate: pulse,
                weight: weight,
                height: height,
                nursing_notes: notes
            });
            showToast('Success', res.message, 'success');
            closeModal('vitals-modal');
            viewPatientProfile(patientId);
        } catch (err) {
            showToast('Save Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });

    // AI Accept Form Submit
    document.getElementById('ai-accept-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const reportId = document.getElementById('ai-accept-report-id').value;
        const notes = document.getElementById('ai-accept-notes').value.trim();

        showAppLoader();
        try {
            const res = await window.API.acceptAIReport(reportId, { feedback_notes: notes });
            showToast('Report Verified', res.message, 'success');
            closeModal('ai-accept-modal');
            if (state.activePage === 'ai_portal' && state.activeAITab === 'history') {
                fetchAIHistory();
            }
        } catch (err) {
            showToast('Acceptance Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });

    // AI Flag Form Submit
    document.getElementById('ai-flag-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const reportId = document.getElementById('ai-flag-report-id').value;
        const reason = document.getElementById('ai-flag-reason').value.trim();

        if (!reason) {
            showToast('Validation Error', 'Please enter reason for flagging.', 'warning');
            return;
        }

        showAppLoader();
        try {
            const res = await window.API.flagAIReport(reportId, reason);
            showToast('Report Flagged', res.message, 'warning');
            closeModal('ai-flag-modal');
            if (state.activePage === 'ai_portal' && state.activeAITab === 'history') {
                fetchAIHistory();
            }
        } catch (err) {
            showToast('Flagging Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });

    // Confirmation Modal Confirm Event
    document.getElementById('confirm-modal-ok-btn').addEventListener('click', () => {
        if (typeof state.confirmCallback === 'function') {
            state.confirmCallback();
        }
    });
}

// ============================================================
// UTILITIES / HELPERS
// ============================================================
function showAppLoader() {
    document.body.classList.add('app-loading');
}

function hideAppLoader() {
    document.body.classList.remove('app-loading');
}

function formatDate(isoStr) {
    if (!isoStr) return '-';
    try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return isoStr;
        
        const pad = (n) => String(n).padStart(2, '0');
        const datePart = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
        const timePart = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
        return `${datePart} ${timePart}`;
    } catch (e) {
        return isoStr;
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ============================================================
// CONFIRMATION DIALOG HANDLERS (DATA REMOVAL & PURGE ACTIONS)
// ============================================================

function confirmDeletePatient(patientId, patientName) {
    openConfirmModal(`⚠️ Are you sure you want to PERMANENTLY delete patient "${patientName}" (${patientId})?\n\nThis will remove all associated appointments, clinical diagnoses, prescriptions, vitals, and AI reports. This action cannot be undone!`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.deletePatient(patientId);
            showToast('Patient Deleted', res.message, 'success');
            if (state.activePatient && state.activePatient.patient_id === patientId) {
                state.activePatient = null;
                navigateTo('patients');
            } else {
                fetchAndRenderPatients();
            }
        } catch (err) {
            showToast('Deletion Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmClearPatientHistory(patientId, patientName) {
    openConfirmModal(`⚠️ Clear all historical records for patient "${patientName}" (${patientId})?\n\nAll recorded diagnoses, prescriptions, vitals, and AI reports will be wiped. The basic patient registration profile will remain intact.`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.clearPatientHistory(patientId);
            showToast('History Cleared', res.message, 'success');
            viewPatientProfile(patientId);
        } catch (err) {
            showToast('Clear Failed', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmDeleteDiagnosis(diagId, patientId) {
    openConfirmModal(`Are you sure you want to delete this diagnosis record?`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.deleteDiagnosis(diagId);
            showToast('Diagnosis Removed', res.message, 'success');
            loadClinicalHistory(patientId);
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmClearDiagnoses(patientId) {
    openConfirmModal(`Are you sure you want to clear ALL past diagnoses recorded for this patient?`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.clearPatientDiagnoses(patientId);
            showToast('Diagnoses Cleared', res.message, 'success');
            loadClinicalHistory(patientId);
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmDeletePrescription(prescId, patientId) {
    openConfirmModal(`Are you sure you want to delete this prescription?`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.deletePrescription(prescId);
            showToast('Prescription Removed', res.message, 'success');
            loadClinicalHistory(patientId);
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmClearPrescriptions(patientId) {
    openConfirmModal(`Are you sure you want to clear ALL prescriptions for this patient?`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.clearPatientPrescriptions(patientId);
            showToast('Prescriptions Cleared', res.message, 'success');
            loadClinicalHistory(patientId);
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmClearVitals(patientId) {
    openConfirmModal(`Are you sure you want to clear the entire vitals history for this patient?`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.clearPatientVitals(patientId);
            showToast('Vitals Cleared', res.message, 'success');
            loadVitalsHistory(patientId);
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmClearAIHistory() {
    openConfirmModal(`⚠️ Are you sure you want to clear past AI diagnostic report logs?\n\nThis will wipe historical AI analyses from view.`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.clearAIHistory();
            showToast('AI History Cleared', res.message, 'success');
            fetchAIHistory();
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmDeleteUser(userId, username) {
    openConfirmModal(`⚠️ PERMANENTLY delete staff account "${username}"?\n\nThis will permanently remove the account and revoke system access. This action cannot be undone!`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.deleteUser(userId);
            showToast('Account Deleted', res.message, 'success');
            renderUsersView();
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

function confirmClearLogs() {
    openConfirmModal(`⚠️ Purge all system activity logs?\n\nThis will permanently wipe both the MySQL activity logs table and physical log files in /logs/ (application.log, security.log, audit.log, error.log).`, async () => {
        closeModal('confirm-modal');
        showAppLoader();
        try {
            const res = await window.API.clearLogs();
            showToast('Logs Purged', res.message, 'success');
            renderLogsView();
        } catch (err) {
            showToast('Error', err.message, 'error');
        } finally {
            hideAppLoader();
        }
    });
}

// Attach functions to window scope for inline HTML events
window.navigateTo = navigateTo;
window.fillLogin = fillLogin;
window.switchAITab = switchAITab;
window.fetchAIHistory = fetchAIHistory;
window.promptAcceptAIReport = promptAcceptAIReport;
window.promptFlagAIReport = promptFlagAIReport;
window.showHistoryDetailModal = showHistoryDetailModal;
window.runDoctorClinicalAI = runDoctorClinicalAI;
window.applyAIDiagnosisToForm = applyAIDiagnosisToForm;
window.applyAIPrescriptionToForm = applyAIPrescriptionToForm;
window.showCreateUserForm = showCreateUserForm;
window.showEditUserForm = showEditUserForm;
window.toggleUserStatus = toggleUserStatus;
window.showRegisterPatientForm = showRegisterPatientForm;
window.showEditPatientForm = showEditPatientForm;
window.viewPatientProfile = viewPatientProfile;
window.showAddDiagnosisForm = showAddDiagnosisForm;
window.showAddPrescriptionForm = showAddPrescriptionForm;
window.showAddVitalsForm = showAddVitalsForm;
window.confirmDeletePatient = confirmDeletePatient;
window.confirmClearPatientHistory = confirmClearPatientHistory;
window.confirmDeleteDiagnosis = confirmDeleteDiagnosis;
window.confirmClearDiagnoses = confirmClearDiagnoses;
window.confirmDeletePrescription = confirmDeletePrescription;
window.confirmClearPrescriptions = confirmClearPrescriptions;
window.confirmClearVitals = confirmClearVitals;
window.confirmClearAIHistory = confirmClearAIHistory;
window.confirmDeleteUser = confirmDeleteUser;
window.confirmClearLogs = confirmClearLogs;
window.escapeHtml = escapeHtml;
