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
        // Clean up legacy API key if present during migration
        localStorage.removeItem('porterApiKey');
    },
    
    isAuthenticated: () => {
        return !!Auth.getToken();
    },
    
    // Check auth state on page load. Call this at the top of protected pages.
    enforceAuth: () => {
        // If we're not on the login page and not authenticated, redirect
        if (!window.location.pathname.includes('login.html') && !Auth.isAuthenticated()) {
            window.location.href = 'login.html';
        }
    },
    
    // Wrap fetch to automatically include the Bearer token and handle 401s
    fetchWithAuth: async (url, options = {}) => {
        const token = Auth.getToken();
        
        // Merge headers safely
        const headers = new Headers(options.headers || {});
        if (token) {
            headers.set('Authorization', `Bearer ${token}`);
        }
        
        const config = { ...options, headers };
        
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
