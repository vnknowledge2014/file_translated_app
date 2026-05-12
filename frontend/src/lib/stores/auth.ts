import { writable } from 'svelte/store';
import { API_BASE } from '$lib/api';

export const isAuthenticated = writable(false);
export const user = writable<{
    username: string;
    wallet_address?: string;
    role?: string;    // user | admin | superadmin
    plan?: string;    // free | pro | enterprise
} | null>(null);

/**
 * Decode a JWT payload (without verification — the server verifies).
 * Used only to extract the username for display purposes on page refresh.
 */
function decodeJwtPayload(token: string): Record<string, any> | null {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        const payload = JSON.parse(atob(parts[1]));
        return payload;
    } catch {
        return null;
    }
}

/** Shorten a wallet address for display: 3ryq...eu3G */
export function shortWallet(addr: string | undefined | null): string {
    if (!addr) return 'User';
    if (addr.length <= 10) return addr;
    return `${addr.slice(0, 4)}...${addr.slice(-4)}`;
}

// Initialize from localStorage if running in browser
if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
        // Immediately set auth state with username from JWT
        const payload = decodeJwtPayload(token);
        const username = payload?.sub || 'User';
        isAuthenticated.set(true);
        user.set({ username });

        // Also fetch /me in background to validate token & get latest user info
        fetch(`${API_BASE}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => {
            if (res.ok) return res.json();
            // Token expired or invalid — log out
            localStorage.removeItem('access_token');
            isAuthenticated.set(false);
            user.set(null);
            return null;
        })
        .then(data => {
            if (data) {
                user.set({
                    username: data.username,
                    wallet_address: data.wallet_address,
                    role: data.role,
                    plan: data.plan,
                });
            }
        })
        .catch(() => {
            // Network error — keep JWT-decoded username
        });
    }
}

export function logout() {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
    }
    isAuthenticated.set(false);
    user.set(null);
    window.location.reload();
}
