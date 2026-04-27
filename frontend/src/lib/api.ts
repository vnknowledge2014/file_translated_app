// The frontend is served on the same host, so API_BASE is empty
export const API_BASE = '';

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
    const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: formData });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data;
}

export async function fetchGlossary(domain: string) {
    const res = await fetch(`${API_BASE}/api/glossary?domain=${domain}`);
    if (!res.ok) throw new Error('Failed to load glossary');
    return await res.json();
}

export async function deleteGlossaryTerm(id: number) {
    const res = await fetch(`${API_BASE}/api/glossary/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete term');
}

export async function uploadGlossary(formData: FormData) {
    const res = await fetch(`${API_BASE}/api/glossary/upload`, { method: 'POST', body: formData });
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.detail || 'Upload failed');
    return data;
}

export async function fetchJobs() {
    const res = await fetch(`${API_BASE}/api/jobs`);
    if (!res.ok) throw new Error('Failed to load jobs');
    return await res.json();
}

export async function downloadJob(jobId: string) {
    window.location.href = `${API_BASE}/api/download/${jobId}`;
}

export async function downloadXliff(jobId: string) {
    window.location.href = `${API_BASE}/api/download/${jobId}/xliff`;
}

export async function uploadXliff(jobId: string, file: File) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/api/upload/${jobId}/xliff`, { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data;
}
