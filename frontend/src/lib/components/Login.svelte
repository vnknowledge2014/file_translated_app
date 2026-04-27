<script lang="ts">
    import { login, API_BASE } from '$lib/api';
    import { isAuthenticated, user } from '$lib/stores/auth';

    let username = '';
    let password = '';
    let error = '';
    let success = '';
    let loading = false;
    let mode: 'login' | 'register' = 'login';

    async function handleLogin() {
        error = '';
        success = '';
        loading = true;
        try {
            await login(username, password);
            isAuthenticated.set(true);
            user.set({ username });
        } catch (e: any) {
            error = e.message || "Failed to login";
        } finally {
            loading = false;
        }
    }

    async function handleRegister() {
        error = '';
        success = '';
        loading = true;
        try {
            const res = await fetch(`${API_BASE}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Registration failed');
            success = `Account "${data.username}" created! You can now log in.`;
            mode = 'login';
        } catch (e: any) {
            error = e.message || "Failed to register";
        } finally {
            loading = false;
        }
    }

    function toggleMode() {
        mode = mode === 'login' ? 'register' : 'login';
        error = '';
        success = '';
    }
</script>

<div class="auth-container">
    <div class="auth-header">
        <div class="logo">📄</div>
        <h2>{mode === 'login' ? 'Translation Portal' : 'Create Account'}</h2>
        <p class="subtitle">
            {mode === 'login' ? 'Sign in to manage your translations' : 'Register a new account'}
        </p>
    </div>

    {#if error}
        <div class="message error">{error}</div>
    {/if}
    {#if success}
        <div class="message success">{success}</div>
    {/if}

    <form on:submit|preventDefault={mode === 'login' ? handleLogin : handleRegister}>
        <div class="form-group">
            <label for="username">Username</label>
            <input id="username" type="text" bind:value={username} placeholder="Enter username" required autocomplete="username" />
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input id="password" type="password" bind:value={password} placeholder="Enter password" required autocomplete={mode === 'login' ? 'current-password' : 'new-password'} />
        </div>

        <button type="submit" disabled={loading}>
            {#if loading}
                <span class="spinner"></span>
                {mode === 'login' ? 'Signing in…' : 'Creating account…'}
            {:else}
                {mode === 'login' ? 'Sign In' : 'Create Account'}
            {/if}
        </button>
    </form>

    <div class="toggle">
        {#if mode === 'login'}
            Don't have an account? <button class="link-btn" on:click={toggleMode}>Register</button>
        {:else}
            Already have an account? <button class="link-btn" on:click={toggleMode}>Sign In</button>
        {/if}
    </div>
</div>

<style>
    .auth-container {
        max-width: 400px;
        margin: 80px auto;
        padding: 2rem;
        background: var(--surface-light, #ffffff);
        border: 1px solid var(--border-light, #e2e8f0);
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }

    .auth-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .logo {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    h2 {
        margin: 0 0 0.25rem;
        color: var(--text-dark, #1a202c);
        font-size: 1.5rem;
        font-weight: 700;
    }

    .subtitle {
        color: var(--text-light, #718096);
        font-size: 0.875rem;
        margin: 0;
    }

    .form-group {
        margin-bottom: 1rem;
    }

    label {
        display: block;
        margin-bottom: 0.375rem;
        font-weight: 500;
        font-size: 0.875rem;
        color: var(--text-dark, #1a202c);
    }

    input {
        width: 100%;
        padding: 0.625rem 0.75rem;
        border: 1px solid var(--border-light, #e2e8f0);
        border-radius: 8px;
        background: var(--surface-light, #ffffff);
        color: var(--text-dark, #1a202c);
        font-size: 0.875rem;
        transition: border-color 0.2s, box-shadow 0.2s;
        box-sizing: border-box;
    }

    input:focus {
        outline: none;
        border-color: var(--primary, #4f46e5);
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
    }

    button[type="submit"] {
        width: 100%;
        padding: 0.75rem;
        margin-top: 0.5rem;
        background: var(--primary, #4f46e5);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.875rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        transition: background 0.2s, transform 0.1s;
    }

    button[type="submit"]:hover:not(:disabled) {
        filter: brightness(1.1);
        transform: translateY(-1px);
    }

    button[type="submit"]:disabled {
        opacity: 0.7;
        cursor: not-allowed;
    }

    .spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255,255,255,0.3);
        border-top-color: white;
        border-radius: 50%;
        animation: spin 0.6s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .message {
        padding: 0.75rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-size: 0.875rem;
    }

    .message.error {
        color: #991b1b;
        background: #fee2e2;
        border: 1px solid #fecaca;
    }

    .message.success {
        color: #166534;
        background: #dcfce7;
        border: 1px solid #bbf7d0;
    }

    .toggle {
        margin-top: 1.25rem;
        text-align: center;
        font-size: 0.8125rem;
        color: var(--text-light, #718096);
    }

    .link-btn {
        background: none;
        border: none;
        color: var(--primary, #4f46e5);
        font-weight: 600;
        cursor: pointer;
        padding: 0;
        font-size: inherit;
    }

    .link-btn:hover {
        text-decoration: underline;
    }
</style>
