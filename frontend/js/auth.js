/**
 * auth.js
 * Centralized Authentication Utility for Agentic Personal Porter
 */

const Auth = {
    TOKEN_KEY: 'porter_jwt',
    
    // Store token in session storage
    setToken: (token) => {
        sessionStorage.setItem(Auth.TOKEN_KEY, token);
    },
    
    getToken: () => {
        return sessionStorage.getItem(Auth.TOKEN_KEY);
    },
    
    clearToken: () => {
        sessionStorage.removeItem(Auth.TOKEN_KEY);
        sessionStorage.removeItem('porter_role');
        sessionStorage.removeItem('porter_account_type');
        // Clean up legacy API key if present during migration
        localStorage.removeItem('porterApiKey');
    },

    logout: () => {
        const adminToken = sessionStorage.getItem('admin_token');
        if (adminToken && sessionStorage.getItem('is_impersonation')) {
            sessionStorage.removeItem('is_impersonation');
            sessionStorage.setItem(Auth.TOKEN_KEY, adminToken);
            sessionStorage.removeItem('admin_token');
            try {
                const payload = JSON.parse(atob(adminToken.split('.')[1]));
                sessionStorage.setItem('porter_role', payload.role);
                sessionStorage.setItem('porter_account_type', payload.account_type);
            } catch(e) {}
            window.location.href = 'admin_index.html';
        } else {
            Auth.clearToken();
            window.location.href = 'login.html';
        }
    },
    
    isAuthenticated: () => {
        return !!Auth.getToken();
    },

    getRole: () => {
        return sessionStorage.getItem('porter_role') || 'user';
    },

    getAccountType: () => {
        return sessionStorage.getItem('porter_account_type') || 'hero';
    },
    
    // Check auth state on page load. Call this at the top of protected pages.
    enforceAuth: () => {
        // If we're not on the login page and not authenticated, redirect
        if (!window.location.pathname.includes('login.html') && !Auth.isAuthenticated()) {
            window.location.href = 'login.html';
        }
    },
    
    // Resolves backend path in case user is viewing via file:/// or live-server instead of app.py
    getApiBaseUrl: () => {
        if (window.location.protocol === 'file:' || window.location.port === '5500') {
            return 'http://127.0.0.1:5090'; // Use localhost explicitly if not served by flask
        }
        return ''; // Let relative paths work if served by Flask
    },
    
    // Wrap fetch to automatically include the Bearer token and handle 401s
    fetchWithAuth: async (endpoint, options = {}) => {
        const token = Auth.getToken();
        
        // Merge headers safely
        const headers = new Headers(options.headers || {});
        if (token) {
            headers.set('Authorization', `Bearer ${token}`);
        }
        
        const config = { ...options, headers };
        const url = endpoint.startsWith('http') ? endpoint : `${Auth.getApiBaseUrl()}${endpoint}`;
        
        try {
            const response = await fetch(url, config);
            
            // If the server rejects our token (expired or invalid), force logout
            if (response.status === 401) {
                console.warn('Authentication rejected by server. Redirecting to login.');
                Auth.clearToken();
                window.location.href = 'login.html';
                // Throw an error to abort any dependent logic in the calling script
                throw new Error("Unauthorized - Session expired");
            }
            
            return response;
        } catch (error) {
            throw error;
        }
    }
};

// Auto-run on load for any script importing this
Auth.enforceAuth();

// Expose to window so type="module" scripts can access it
window.Auth = Auth;
