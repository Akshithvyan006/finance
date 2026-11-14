/**
 * API Client Module for FinSec AI
 * Handles authenticated fetch requests, JWT Bearer tokens, and error handling.
 */

const Api = (() => {
    const TOKEN_KEY = "finsec_jwt_token";
    const USER_KEY = "finsec_user_data";

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        if (token) {
            localStorage.setItem(TOKEN_KEY, token);
        } else {
            localStorage.removeItem(TOKEN_KEY);
        }
    }

    function getUser() {
        try {
            return JSON.parse(localStorage.getItem(USER_KEY));
        } catch {
            return null;
        }
    }

    function setUser(user) {
        if (user) {
            localStorage.setItem(USER_KEY, JSON.stringify(user));
        } else {
            localStorage.removeItem(USER_KEY);
        }
    }

    function clearSession() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    }

    async function request(endpoint, options = {}) {
        const url = endpoint.startsWith("http") ? endpoint : endpoint;
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        };

        const token = getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers,
        };

        if (options.body && typeof options.body === "object") {
            config.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                // Handle 401 Unauthorized globally
                if (response.status === 401 && !endpoint.includes("/auth/login")) {
                    clearSession();
                    window.dispatchEvent(new CustomEvent("finsec:unauthorized"));
                }
                const errorMsg = data.error || data.message || `Request failed (${response.status})`;
                const error = new Error(errorMsg);
                error.status = response.status;
                error.data = data;
                throw error;
            }

            return data;
        } catch (err) {
            console.error(`[API Error] ${endpoint}:`, err);
            throw err;
        }
    }

    return {
        getToken,
        setToken,
        getUser,
        setUser,
        clearSession,
        get: (endpoint) => request(endpoint, { method: "GET" }),
        post: (endpoint, body) => request(endpoint, { method: "POST", body }),
        put: (endpoint, body) => request(endpoint, { method: "PUT", body }),
        delete: (endpoint) => request(endpoint, { method: "DELETE" }),
    };
})();
