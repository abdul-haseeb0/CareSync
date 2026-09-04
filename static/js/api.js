/**
 * CareSync - API Service Library
 */

const API_BASE = '/api';

async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    
    // Auto handle JSON headers vs FormData
    const isFormData = options.body instanceof FormData;
    if (!isFormData) {
        options.headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
    }

    try {
        const response = await fetch(url, options);
        let data = {};
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        }

        if (!response.ok) {
            const error = new Error(data.message || response.statusText || 'An error occurred');
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    } catch (err) {
        if (err.status) throw err;
        const networkError = new Error(err.message || 'Network error or server unavailable');
        networkError.status = 500;
        throw networkError;
    }
}

const API = {
    // Auth
    async login(username, password) {
        return request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    async logout() {
        return request('/auth/logout', {
            method: 'POST'
        });
    },

    async getSession() {
        return request('/auth/session', {
            method: 'GET'
        });
    },

    // Admin Users
    async getUsers() {
        return request('/admin/users', {
            method: 'GET'
        });
    },

    async createUser(userData) {
        return request('/admin/users', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    },

    async updateUser(userId, userData) {
        return request(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData)
        });
    },

    async toggleUserStatus(userId) {
        return request(`/admin/users/${userId}/status`, {
            method: 'PATCH'
        });
    },

    async getLogs() {
        return request('/admin/logs', {
            method: 'GET'
        });
    },

    // Patients
    async getPatients({ search = '', sort = 'patient_id', order = 'asc', page = 1, limit = 10 } = {}) {
        const params = new URLSearchParams({ search, sort, order, page, limit });
        return request(`/patients?${params.toString()}`, {
            method: 'GET'
        });
    },

    async registerPatient(patientData) {
        return request('/patients', {
            method: 'POST',
            body: JSON.stringify(patientData)
        });
    },

    async getPatient(patientId) {
        return request(`/patients/${patientId}`, {
            method: 'GET'
        });
    },

    async updatePatient(patientId, patientData) {
        return request(`/patients/${patientId}`, {
            method: 'PUT',
            body: JSON.stringify(patientData)
        });
    },

    // Clinical Records (Doctor only)
    async getClinicalRecords(patientId) {
        return request(`/patients/${patientId}/clinical`, {
            method: 'GET'
        });
    },

    async addDiagnosis(patientId, diagnosisData) {
        return request(`/patients/${patientId}/diagnoses`, {
            method: 'POST',
            body: JSON.stringify(diagnosisData)
        });
    },

    async addPrescription(patientId, prescriptionData) {
        return request(`/patients/${patientId}/prescriptions`, {
            method: 'POST',
            body: JSON.stringify(prescriptionData)
        });
    },

    // Vitals Records (Nurse/Doctor)
    async getVitals(patientId) {
        return request(`/patients/${patientId}/vitals`, {
            method: 'GET'
        });
    },

    async addVitals(patientId, vitalsData) {
        return request(`/patients/${patientId}/vitals`, {
            method: 'POST',
            body: JSON.stringify(vitalsData)
        });
    },

    // Stats
    async getStats() {
        return request('/stats', {
            method: 'GET'
        });
    },

    // ========================================================
    // AI DIAGNOSTIC PORTAL APIS
    // ========================================================
    async analyzeRadiology(formData) {
        return request('/ai/radiology/analyze', {
            method: 'POST',
            body: formData // FormData object containing image, modality, body_part, clinical_notes, patient_id
        });
    },

    async analyzeLabReport(formData) {
        return request('/ai/lab/analyze', {
            method: 'POST',
            body: formData // FormData object or json
        });
    },

    async clinicalAssistant(clinicalData) {
        return request('/ai/clinical/assist', {
            method: 'POST',
            body: JSON.stringify(clinicalData)
        });
    },

    async acceptAIReport(reportId, data = {}) {
        return request(`/ai/reports/${reportId}/accept`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async flagAIReport(reportId, reason) {
        return request(`/ai/reports/${reportId}/flag`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
    },

    async deleteUser(userId) {
        return request(`/admin/users/${userId}`, {
            method: 'DELETE'
        });
    },

    async clearLogs() {
        return request('/admin/logs/clear', {
            method: 'POST'
        });
    },

    async deletePatient(patientId) {
        return request(`/patients/${patientId}`, {
            method: 'DELETE'
        });
    },

    async clearPatientHistory(patientId) {
        return request(`/patients/${patientId}/history/clear`, {
            method: 'POST'
        });
    },

    async deleteDiagnosis(diagnosisId) {
        return request(`/diagnoses/${diagnosisId}`, {
            method: 'DELETE'
        });
    },

    async clearPatientDiagnoses(patientId) {
        return request(`/patients/${patientId}/diagnoses/clear`, {
            method: 'POST'
        });
    },

    async deletePrescription(prescriptionId) {
        return request(`/prescriptions/${prescriptionId}`, {
            method: 'DELETE'
        });
    },

    async clearPatientPrescriptions(patientId) {
        return request(`/patients/${patientId}/prescriptions/clear`, {
            method: 'POST'
        });
    },

    async clearPatientVitals(patientId) {
        return request(`/patients/${patientId}/vitals/clear`, {
            method: 'POST'
        });
    },

    async clearAIHistory() {
        return request('/ai/history/clear', {
            method: 'POST'
        });
    },

    async getAIHistory({ type = '', status = '', search = '' } = {}) {
        const params = new URLSearchParams();
        if (type) params.append('type', type);
        if (status) params.append('status', status);
        if (search) params.append('search', search);
        return request(`/ai/history?${params.toString()}`, {
            method: 'GET'
        });
    }
};

window.API = API;
