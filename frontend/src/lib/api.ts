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

export async function login(username: string, password: string) {
    const fd = new FormData();
    fd.append('username', username);
    fd.append('password', password);
    const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        body: fd
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    localStorage.setItem('access_token', data.access_token);
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
