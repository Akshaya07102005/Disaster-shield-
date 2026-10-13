// Shared API Wrapper for Disaster Shield AI
const RENDER_BACKEND_URL = 'https://disaster-shield-backend-u54q.onrender.com';

// Intelligent API base URL detection:
// - If running directly on Render or local Flask port 5000: relative URL '' is used
// - If deployed on Vercel or running on another port: route to live Render backend URL
const API_URL = (window.location.origin.includes('onrender.com') || window.location.port === '5000')
    ? ''
    : RENDER_BACKEND_URL;

const api = {
    getBackendUrl: () => API_URL || window.location.origin,
    getSocketUrl: () => API_URL || window.location.origin,
    getToken: () => localStorage.getItem('access_token'),
    setToken: (token) => {
        localStorage.setItem('access_token', token);
        // Also set token in cookie for Flask JWT Extended
        document.cookie = `access_token_cookie=${token}; path=/; max-age=43200; SameSite=Lax`;
    },
    clearToken: () => {
        localStorage.removeItem('access_token');
        document.cookie = 'access_token_cookie=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC; SameSite=Lax';
    },
    getUser: () => {
        const u = localStorage.getItem('user');
        return u ? JSON.parse(u) : null;
    },
    setUser: (user) => localStorage.setItem('user', JSON.stringify(user)),
    getNgo: () => {
        const n = localStorage.getItem('ngo');
        return n ? JSON.parse(n) : null;
    },
    setNgo: (ngo) => localStorage.setItem('ngo', JSON.stringify(ngo)),
    
    // Core Fetch Wrapper
    request: async (endpoint, options = {}) => {
        const url = `${API_URL}${endpoint}`;
        const token = api.getToken();
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const config = {
            ...options,
            headers
        };
        
        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Unauthorized, redirect to login
                api.clearToken();
                if (window.location.pathname !== '/' && window.location.pathname !== '/index.html') {
                    window.location.href = '/';
                }
            }
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || 'Request failed');
            }
            return data;
        } catch (error) {
            console.error('API Error:', error.message);
            throw error;
        }
    },
    
    // Auth endpoints
    login: async (email, password) => {
        const data = await api.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        if (data.access_token) {
            api.setToken(data.access_token);
            api.setUser(data.user);
            if (data.ngo) {
                api.setNgo(data.ngo);
            } else {
                localStorage.removeItem('ngo');
            }
        }
        return data;
    },
    
    register: async (registerData) => {
        return await api.request('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(registerData)
        });
    },
    
    logout: async () => {
        try {
            await api.request('/api/auth/logout', { method: 'POST' });
        } catch (e) {}
        api.clearToken();
        localStorage.removeItem('user');
        localStorage.removeItem('ngo');
        window.location.href = '/';
    },
    
    checkSession: async () => {
        try {
            const data = await api.request('/api/auth/me');
            api.setUser(data.user);
            if (data.ngo) {
                api.setNgo(data.ngo);
            }
            return data;
        } catch (e) {
            api.clearToken();
            return null;
        }
    },
    
    redirectBasedOnRole: (role) => {
        if (role === 'gov') {
            window.location.href = '/government/dashboard.html';
        } else if (role === 'citizen') {
            window.location.href = '/citizen/dashboard.html';
        } else if (role === 'ngo') {
            window.location.href = '/ngo/dashboard.html';
        } else {
            window.location.href = '/';
        }
    }
};
