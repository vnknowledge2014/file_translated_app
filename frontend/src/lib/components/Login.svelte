<script lang="ts">
    import { login } from '$lib/api';
    import { isAuthenticated, user } from '$lib/stores/auth';

    let username = '';
    let password = '';
    let error = '';
    let loading = false;

    async function handleLogin() {
        error = '';
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
</script>

<div class="login-container">
    <h2>Login to Translation Portal</h2>
    
    {#if error}
        <div class="error">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleLogin}>
        <div class="form-group">
            <label for="username">Username</label>
            <input id="username" type="text" bind:value={username} required />
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input id="password" type="password" bind:value={password} required />
        </div>
        
        <button type="submit" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
        </button>
        
        <p class="hint">For testing, you can use the API directly to register a user at <code>/api/auth/register</code></p>
    </form>
</div>

<style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 2rem;
        background: var(--surface-light);
        border: 1px solid var(--border-light);
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    h2 {
        margin-bottom: 1.5rem;
        color: var(--text-dark);
        text-align: center;
    }
    
    .form-group {
        margin-bottom: 1rem;
    }
    
    label {
        display: block;
        margin-bottom: 0.5rem;
        font-weight: 500;
        color: var(--text-dark);
    }
    
    input {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid var(--border-light);
        border-radius: 6px;
        background: var(--surface-light);
        color: var(--text-dark);
    }
    
    button {
        width: 100%;
        padding: 0.75rem;
        margin-top: 1rem;
        background: var(--primary);
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
    }
    
    button:disabled {
        opacity: 0.7;
        cursor: not-allowed;
    }
    
    .error {
        color: #ef4444;
        background: #fee2e2;
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        font-size: 0.875rem;
    }
    
    .hint {
        margin-top: 1rem;
        font-size: 0.75rem;
        color: var(--text-light);
        text-align: center;
    }
</style>
