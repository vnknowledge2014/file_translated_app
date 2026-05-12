// The frontend is served on the same host, so API_BASE is empty
export const API_BASE = '';

function getHeaders(isFormData: boolean = false): HeadersInit {
    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (!isFormData) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
}

/** Wrapper around fetch that auto-handles 401 by logging out */
async function authFetch(url: string, init?: RequestInit): Promise<Response> {
    const res = await fetch(url, init);
    if (res.status === 401) {
        localStorage.removeItem('access_token');
        window.location.reload();
    }
    return res;
}

// ── Auth is handled via Phantom wallet (walletChallenge + walletVerify) ──

export async function fetchMe() {
    const res = await authFetch(`${API_BASE}/api/auth/me`, { headers: getHeaders() });
    if (!res.ok) return null;
    return await res.json();
}

export async function updateUsername(username: string) {
    const res = await authFetch(`${API_BASE}/api/auth/me`, {
        method: 'PUT',
        headers: { ...getHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ username }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update username');
    return data;
}

// ── Wallet Auth (Phantom) ──

export async function walletChallenge(walletAddress: string) {
    const res = await fetch(`${API_BASE}/api/auth/wallet/challenge`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: walletAddress }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to get challenge');
    return data;
}

export async function walletVerify(walletAddress: string, signature: string, nonce: string) {
    const res = await fetch(`${API_BASE}/api/auth/wallet/verify`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: walletAddress, signature, nonce }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Invalid signature');
    localStorage.setItem('access_token', data.access_token);
    return data;
}

export async function walletLink(walletAddress: string, signature: string, nonce: string) {
    const res = await authFetch(`${API_BASE}/api/auth/wallet/link`, {
        method: 'POST', headers: getHeaders(),
        body: JSON.stringify({ wallet_address: walletAddress, signature, nonce }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to link wallet');
    return data;
}

// ── Billing ──

export async function getBillingStatus() {
    const res = await authFetch(`${API_BASE}/api/billing/status`, { headers: getHeaders() });
    if (!res.ok) return null;
    return await res.json();
}

export async function createPayment(plan: string) {
    const res = await authFetch(`${API_BASE}/api/billing/create-payment`, {
        method: 'POST', headers: getHeaders(),
        body: JSON.stringify({ plan }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to create payment');
    return data;
}

export async function confirmPayment(reference: string, txSignature: string) {
    const res = await authFetch(`${API_BASE}/api/billing/confirm-payment`, {
        method: 'POST', headers: getHeaders(),
        body: JSON.stringify({ reference, tx_signature: txSignature }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to confirm payment');
    return data;
}

export async function fetchLanguages() {
    const res = await fetch(`${API_BASE}/api/languages`);
    if (!res.ok) throw new Error('Failed to load languages');
    return await res.json();
}

export async function fetchDomains() {
    const res = await fetch(`${API_BASE}/api/domains`);
    if (!res.ok) throw new Error('Failed to load domains');
    return await res.json();
}

export async function uploadDocument(formData: FormData) {
    const res = await authFetch(`${API_BASE}/api/upload`, { 
        method: 'POST', 
        body: formData,
        headers: getHeaders(true)
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data;
}

export async function fetchGlossary(domain: string) {
    const res = await authFetch(`${API_BASE}/api/glossary?domain=${domain}`, {
        headers: getHeaders()
    });
    if (!res.ok) throw new Error('Failed to load glossary');
    return await res.json();
}

export async function deleteGlossaryTerm(id: string) {
    const res = await authFetch(`${API_BASE}/api/glossary/${id}`, { 
        method: 'DELETE',
        headers: getHeaders()
    });
    if (!res.ok) throw new Error('Failed to delete term');
}

export async function uploadGlossary(formData: FormData) {
    const res = await authFetch(`${API_BASE}/api/glossary/upload`, { 
        method: 'POST', 
        body: formData,
        headers: getHeaders(true)
    });
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.detail || 'Upload failed');
    return data;
}

export async function fetchJobs() {
    const res = await authFetch(`${API_BASE}/api/jobs`, {
        headers: getHeaders()
    });
    if (!res.ok) throw new Error('Failed to load jobs');
    return await res.json();
}

/** 
 * Subscribe to job status updates via SSE.
 * Uses fetch + ReadableStream instead of EventSource to allow custom headers (via authFetch)
 * and seamless fallback/reconnect.
 */
export function subscribeJobEvents(callbacks: {
    onInit: (jobs: any[]) => void;
    onProgress: (data: any) => void;
    onCompleted: (data: any) => void;
    onFailed: (data: any) => void;
    onQueued: (data: any) => void;
}): () => void {
    let es: EventSource | null = null;
    let isIntentionallyClosed = false;
    let reconnectTimer: any;
    
    const token = localStorage.getItem('access_token');
    if (!token) return () => {};

    function connect() {
        if (isIntentionallyClosed) return;
        
        es = new EventSource(`${API_BASE}/api/jobs/stream?token=${token}`);
        
        es.addEventListener('init', (e) => {
            try { callbacks.onInit(JSON.parse(e.data)); } catch (err) { console.error(err); }
        });
        
        es.addEventListener('progress', (e) => {
            try { callbacks.onProgress(JSON.parse(e.data)); } catch (err) { console.error(err); }
        });
        
        es.addEventListener('completed', (e) => {
            try { callbacks.onCompleted(JSON.parse(e.data)); } catch (err) { console.error(err); }
        });
        
        es.addEventListener('failed', (e) => {
            try { callbacks.onFailed(JSON.parse(e.data)); } catch (err) { console.error(err); }
        });

        es.addEventListener('queued', (e) => {
            try { callbacks.onQueued(JSON.parse(e.data)); } catch (err) { console.error(err); }
        });
        
        es.onerror = (err) => {
            // Trình duyệt tự reconnect ở mức độ network, nhưng nếu server trả 502/504,
            // EventSource có thể sẽ từ bỏ và chuyển trạng thái sang CLOSED (2).
            if (es && es.readyState === EventSource.CLOSED) {
                console.warn('SSE connection closed unexpectedly. Initiating manual reconnect in 3s...');
                es.close();
                clearTimeout(reconnectTimer);
                // Tạo lại connection mới sau 3 giây để bypass cơ chế bỏ cuộc của trình duyệt
                reconnectTimer = setTimeout(connect, 3000);
            } else {
                console.warn('SSE transient error, letting browser auto-reconnect...', err);
            }
        };
    }

    // Khởi chạy kết nối lần đầu
    connect();
    
    // Cleanup function trả về cho Svelte component onDestroy
    return () => {
        isIntentionallyClosed = true;
        clearTimeout(reconnectTimer);
        if (es) {
            es.close();
        }
    };
}

export async function downloadJob(jobId: string) {
    const res = await authFetch(`${API_BASE}/api/download/${jobId}`, {
        headers: getHeaders()
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.error || 'Failed to download file');
    }
    
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    
    // Attempt to extract filename from Content-Disposition header if possible
    let filename = `job_${jobId}_vi`;
    const disposition = res.headers.get('content-disposition');
    if (disposition && disposition.indexOf('filename=') !== -1) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        if (matches != null && matches[1]) { 
            filename = matches[1].replace(/['"]/g, '');
        }
    }
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

export async function downloadXliff(jobId: string) {
    const res = await authFetch(`${API_BASE}/api/download/${jobId}?xliff=true`, {
        headers: getHeaders()
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.error || 'Failed to download XLIFF');
    }
    
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `job_${jobId}_vi.xlf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

export async function uploadXliff(jobId: string, file: File) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await authFetch(`${API_BASE}/api/upload/${jobId}/xliff`, { 
        method: 'POST', 
        body: fd,
        headers: getHeaders(true)
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data;
}

export async function retryJob(jobId: string) {
    const res = await authFetch(`${API_BASE}/api/jobs/${jobId}/retry`, {
        method: 'POST',
        headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to retry job');
    return data;
}

export async function deleteJob(jobId: string) {
    const res = await authFetch(`${API_BASE}/api/jobs/${jobId}`, {
        method: 'DELETE',
        headers: getHeaders(),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to delete job');
    }
    return await res.json();
}

// ── API Key Management ──

export interface ApiKeyInfo {
    id: string;
    name: string;
    key_prefix: string;
    scope: string;
    requests_count: number;
    requests_limit: number | null;
    pages_used: number;
    pages_limit: number | null;
    last_used: string | null;
    is_active: boolean;
    created_at: string;
}

export interface CreateKeyResponse {
    id: string;
    name: string;
    key: string;
    key_prefix: string;
    scope: string;
    message: string;
}

export async function createApiKey(name: string, scope: string = 'translate'): Promise<CreateKeyResponse> {
    const res = await authFetch(`${API_BASE}/api/keys`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ name, scope }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to create API key');
    return data;
}

export async function listApiKeys(): Promise<ApiKeyInfo[]> {
    const res = await authFetch(`${API_BASE}/api/keys`, {
        headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load API keys');
    return await res.json();
}

export async function deleteApiKey(id: string): Promise<void> {
    const res = await authFetch(`${API_BASE}/api/keys/${id}`, {
        method: 'DELETE',
        headers: getHeaders(),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to revoke API key');
    }
}

// ── Admin Dashboard ──

export async function adminGetStats() {
    const res = await authFetch(`${API_BASE}/api/admin/stats`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load admin stats');
    return await res.json();
}

export async function adminListUsers(params: {
    page?: number; limit?: number; search?: string; plan?: string; role?: string;
} = {}) {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.limit) qs.set('limit', String(params.limit));
    if (params.search) qs.set('search', params.search);
    if (params.plan) qs.set('plan', params.plan);
    if (params.role) qs.set('role', params.role);
    const res = await authFetch(`${API_BASE}/api/admin/users?${qs}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load users');
    return await res.json();
}

export async function adminGetUser(userId: string) {
    const res = await authFetch(`${API_BASE}/api/admin/users/${userId}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load user detail');
    return await res.json();
}

export async function adminUpdateUser(userId: string, data: Record<string, any>) {
    const res = await authFetch(`${API_BASE}/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Failed to update user');
    return result;
}

export async function adminDisableUser(userId: string, isActive: boolean) {
    const res = await authFetch(`${API_BASE}/api/admin/users/${userId}/disable`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ is_active: isActive }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Failed to update user status');
    return result;
}

export async function adminListJobs(params: {
    page?: number; limit?: number; status?: string; owner_id?: string;
} = {}) {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.limit) qs.set('limit', String(params.limit));
    if (params.status) qs.set('status', params.status);
    if (params.owner_id) qs.set('owner_id', params.owner_id);
    const res = await authFetch(`${API_BASE}/api/admin/jobs?${qs}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load jobs');
    return await res.json();
}

export async function adminDeleteJob(jobId: string) {
    const res = await authFetch(`${API_BASE}/api/admin/jobs/${jobId}`, {
        method: 'DELETE',
        headers: getHeaders(),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to delete job');
    }
}

export async function adminGetRevenue(period: string = '30d') {
    const res = await authFetch(`${API_BASE}/api/admin/billing/revenue?period=${period}`, {
        headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load revenue data');
    return await res.json();
}

export async function adminGetPayments(page: number = 1) {
    const res = await authFetch(`${API_BASE}/api/admin/billing/payments?page=${page}`, {
        headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load payments');
    return await res.json();
}

export async function adminGetHealth() {
    const res = await authFetch(`${API_BASE}/api/admin/system/health`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load system health');
    return await res.json();
}

export async function adminGetConfig() {
    const res = await authFetch(`${API_BASE}/api/admin/system/config`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load config');
    return await res.json();
}

export async function adminUpdateConfig(data: Record<string, any>) {
    const res = await authFetch(`${API_BASE}/api/admin/system/config`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Failed to update config');
    return result;
}

