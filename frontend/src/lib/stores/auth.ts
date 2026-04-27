import { writable } from 'svelte/store';

export const isAuthenticated = writable(false);
export const user = writable<{username: string} | null>(null);

// Initialize from localStorage if running in browser
if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
        isAuthenticated.set(true);
        // We could decode JWT to get username, but simply showing "Logged in" is fine for now
        user.set({username: "User"});
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
