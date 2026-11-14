/**
 * FinSec AI - Application Controller
 * Handles application lifecycle, RBAC view switching, authentication modals, and notifications.
 */

window.App = (() => {
    let currentUser = null;

    function init() {
        initTheme();
        initNavigation();
        initAuthModals();
        initDemoButtons();

        // Initialize submodules
        Chatbot.init();
        Calculators.init();
        Analyst.init();
        Admin.init();

        // Check active session on startup
        checkAuthSession();

        // Global unauthorized event listener
        window.addEventListener("finsec:unauthorized", () => {
            updateAuthUI(null);
            showToast("Session expired or unauthorized. Please sign in.", "warning");
        });
    }

    // -------------------------------------------------------------------------
    // Theme Management (Dark / Light)
    // -------------------------------------------------------------------------
    function initTheme() {
        const toggleBtn = document.getElementById("themeToggleBtn");
        const savedTheme = localStorage.getItem("finsec_theme") || "dark";
        document.documentElement.setAttribute("data-theme", savedTheme);

        toggleBtn?.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme");
            const next = current === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", next);
            localStorage.setItem("finsec_theme", next);
        });
    }

    // -------------------------------------------------------------------------
    // Navigation & Tab Switching
    // -------------------------------------------------------------------------
    function initNavigation() {
        const tabs = document.querySelectorAll(".nav-tab");
        tabs.forEach(tab => {
            tab.addEventListener("click", () => {
                const targetId = tab.dataset.tab;
                switchTab(targetId);
            });
        });
    }

    function switchTab(tabId) {
        document.querySelectorAll(".nav-tab").forEach(t => {
            t.classList.toggle("active", t.dataset.tab === tabId);
        });

        document.querySelectorAll(".tab-pane").forEach(pane => {
            pane.classList.toggle("active", pane.id === tabId);
        });

        // Trigger tab-specific data refresh
        if (tabId === "tab-user-dashboard") {
            loadUserDashboard();
        } else if (tabId === "tab-analyst") {
            Analyst.loadAnalystWorkspace();
        } else if (tabId === "tab-admin") {
            Admin.loadAdminWorkspace();
        }
    }

    // -------------------------------------------------------------------------
    // Authentication & Session Management
    // -------------------------------------------------------------------------
    async function checkAuthSession() {
        if (!Api.getToken()) {
            updateAuthUI(null);
            // Default to demo user for instantaneous interactive testing
            loginWithDemo("user_john", "UserPassword!2026", false);
            return;
        }

        try {
            const res = await Api.get("/api/v1/auth/me");
            currentUser = res.user;
            Api.setUser(res.user);
            updateAuthUI(res.user);
        } catch (err) {
            Api.clearSession();
            updateAuthUI(null);
        }
    }

    function updateAuthUI(user) {
        currentUser = user;
        const userPill = document.getElementById("userPill");
        const authActions = document.getElementById("authActions");
        const tabAnalyst = document.getElementById("tabBtnAnalyst");
        const tabAdmin = document.getElementById("tabBtnAdmin");

        if (user) {
            userPill.style.display = "flex";
            authActions.style.display = "none";

            document.getElementById("userNameLabel").textContent = user.username;
            document.getElementById("userRoleBadge").textContent = user.role;
            document.getElementById("userAvatar").textContent = user.username.charAt(0).toUpperCase();

            // Set role colors
            const roleBadge = document.getElementById("userRoleBadge");
            if (user.role === "Admin") roleBadge.style.color = "var(--role-admin)";
            else if (user.role === "Financial Analyst") roleBadge.style.color = "var(--role-analyst)";
            else roleBadge.style.color = "var(--role-user)";

            // RBAC Tab Visibility
            if (tabAnalyst) {
                tabAnalyst.style.display = (user.role === "Financial Analyst" || user.role === "Admin") ? "flex" : "none";
            }
            if (tabAdmin) {
                tabAdmin.style.display = (user.role === "Admin") ? "flex" : "none";
            }
        } else {
            userPill.style.display = "none";
            authActions.style.display = "flex";

            if (tabAnalyst) tabAnalyst.style.display = "none";
            if (tabAdmin) tabAdmin.style.display = "none";

            // If active tab was restricted, fallback to Chatbot
            const activeTab = document.querySelector(".nav-tab.active")?.dataset.tab;
            if (activeTab === "tab-analyst" || activeTab === "tab-admin") {
                switchTab("tab-chat");
            }
        }
    }

    function initAuthModals() {
        const loginModal = document.getElementById("loginModal");
        const registerModal = document.getElementById("registerModal");

        document.getElementById("openLoginModalBtn")?.addEventListener("click", () => openModal(loginModal));
        document.getElementById("openRegisterModalBtn")?.addEventListener("click", () => openModal(registerModal));

        document.querySelectorAll("[data-close-modal]").forEach(btn => {
            btn.addEventListener("click", () => {
                closeModal(loginModal);
                closeModal(registerModal);
            });
        });

        // Login form submit
        document.getElementById("loginForm")?.addEventListener("submit", async (e) => {
            e.preventDefault();
            const userOrEmail = document.getElementById("loginUser").value.trim();
            const pass = document.getElementById("loginPass").value;

            try {
                const res = await Api.post("/api/v1/auth/login", {
                    username_or_email: userOrEmail,
                    password: pass,
                });
                Api.setToken(res.token);
                Api.setUser(res.user);
                updateAuthUI(res.user);
                closeModal(loginModal);
                showToast(`Welcome back, ${res.user.username} (${res.user.role})!`, "success");
            } catch (err) {
                showToast(err.message || "Login failed.", "error");
            }
        });

        // Register form submit
        document.getElementById("registerForm")?.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("regUsername").value.trim();
            const email = document.getElementById("regEmail").value.trim();
            const pass = document.getElementById("regPassword").value;

            try {
                const res = await Api.post("/api/v1/auth/register", {
                    username,
                    email,
                    password: pass,
                });
                showToast("Account created successfully! Please sign in.", "success");
                closeModal(registerModal);
                openModal(loginModal);
            } catch (err) {
                showToast(err.message || "Registration failed.", "error");
            }
        });

        // Logout
        document.getElementById("logoutBtn")?.addEventListener("click", async () => {
            try {
                await Api.post("/api/v1/auth/logout");
            } catch (err) {
                console.warn("Logout error:", err);
            } finally {
                Api.clearSession();
                updateAuthUI(null);
                showToast("Logged out successfully. Token revoked.", "info");
            }
        });
    }

    function initDemoButtons() {
        document.getElementById("demoUserBtn")?.addEventListener("click", () => {
            loginWithDemo("user_john", "UserPassword!2026");
        });
        document.getElementById("demoAnalystBtn")?.addEventListener("click", () => {
            loginWithDemo("analyst_jane", "AnalystSecure!2026");
        });
        document.getElementById("demoAdminBtn")?.addEventListener("click", () => {
            loginWithDemo("admin_sec", "AdminPassword!2026");
        });
    }

    async function loginWithDemo(username, password, showNotification = true) {
        try {
            const res = await Api.post("/api/v1/auth/login", {
                username_or_email: username,
                password: password,
            });
            Api.setToken(res.token);
            Api.setUser(res.user);
            updateAuthUI(res.user);

            if (showNotification) {
                showToast(`Switched to demo role: ${res.user.role} (${res.user.username})`, "success");
            }
        } catch (err) {
            console.error("Demo login error:", err);
        }
    }

    // -------------------------------------------------------------------------
    // User Financial Dashboard Data
    // -------------------------------------------------------------------------
    async function loadUserDashboard() {
        if (!Api.getToken()) {
            showToast("Please sign in to view your private financial records.", "info");
            return;
        }

        try {
            const data = await Api.get("/api/v1/user/summary");
            const summary = data.summary;

            document.getElementById("statBudgetCount").textContent = summary.saved_budgets_count;
            document.getElementById("statGoalsCount").textContent = summary.savings_goals_count;
            document.getElementById("statTotalSavings").textContent = `$${summary.total_projected_savings.toLocaleString()}`;
            document.getElementById("statTotalDebt").textContent = `$${summary.total_loan_balances.toLocaleString()}`;

            renderUserBudgets();
            renderUserSavings();
            renderUserLoans();
        } catch (err) {
            console.error("Failed to load user summary:", err);
        }
    }

    async function renderUserBudgets() {
        const tbody = document.querySelector("#savedBudgetsTable tbody");
        if (!tbody) return;

        try {
            const data = await Api.get("/api/v1/user/budgets");
            if (!data.budgets || data.budgets.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No saved budgets. Save one from the Calculators tab!</td></tr>`;
                return;
            }

            tbody.innerHTML = data.budgets.map(b => `
                <tr>
                    <td><strong>$${b.monthly_income.toLocaleString()}</strong></td>
                    <td>$${b.needs_amount.toLocaleString()}</td>
                    <td>$${b.wants_amount.toLocaleString()}</td>
                    <td>$${b.savings_amount.toLocaleString()}</td>
                    <td class="text-muted">${escapeHtml(b.notes || "-")}</td>
                    <td>
                        <button class="btn-delete" onclick="window.App.deleteBudget(${b.id})">Delete</button>
                    </td>
                </tr>
            `).join("");
        } catch (err) {
            console.error(err);
        }
    }

    async function renderUserSavings() {
        const tbody = document.querySelector("#savedGoalsTable tbody");
        if (!tbody) return;

        try {
            const data = await Api.get("/api/v1/user/savings-goals");
            if (!data.savings_goals || data.savings_goals.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No saved goals yet.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.savings_goals.map(g => `
                <tr>
                    <td><strong>${escapeHtml(g.title)}</strong></td>
                    <td>$${g.monthly_contribution.toLocaleString()}</td>
                    <td>${g.annual_interest_rate}%</td>
                    <td>${g.time_horizon_years} yrs</td>
                    <td class="text-success"><strong>$${g.projected_total.toLocaleString()}</strong></td>
                    <td>
                        <button class="btn-delete" onclick="window.App.deleteSavingsGoal(${g.id})">Delete</button>
                    </td>
                </tr>
            `).join("");
        } catch (err) {
            console.error(err);
        }
    }

    async function renderUserLoans() {
        const tbody = document.querySelector("#savedLoansTable tbody");
        if (!tbody) return;

        try {
            const data = await Api.get("/api/v1/user/loans");
            if (!data.loans || data.loans.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No loan scenarios saved yet.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.loans.map(l => `
                <tr>
                    <td><strong>${escapeHtml(l.loan_name)}</strong></td>
                    <td>$${l.principal.toLocaleString()}</td>
                    <td>${l.annual_rate}%</td>
                    <td>${l.term_months} mos</td>
                    <td class="text-brand"><strong>$${l.monthly_payment.toLocaleString()}</strong></td>
                    <td class="text-warning">$${l.total_interest.toLocaleString()}</td>
                    <td>
                        <button class="btn-delete" onclick="window.App.deleteLoan(${l.id})">Delete</button>
                    </td>
                </tr>
            `).join("");
        } catch (err) {
            console.error(err);
        }
    }

    async function deleteBudget(id) {
        if (!confirm("Are you sure you want to delete this budget?")) return;
        try {
            await Api.delete(`/api/v1/user/budgets/${id}`);
            showToast("Budget deleted successfully.", "success");
            loadUserDashboard();
        } catch (err) {
            showToast(err.message || "Failed to delete.", "error");
        }
    }

    async function deleteSavingsGoal(id) {
        if (!confirm("Are you sure you want to delete this savings goal?")) return;
        try {
            await Api.delete(`/api/v1/user/savings-goals/${id}`);
            showToast("Savings goal deleted.", "success");
            loadUserDashboard();
        } catch (err) {
            showToast(err.message || "Failed to delete.", "error");
        }
    }

    async function deleteLoan(id) {
        if (!confirm("Are you sure you want to delete this loan scenario?")) return;
        try {
            await Api.delete(`/api/v1/user/loans/${id}`);
            showToast("Loan scenario deleted.", "success");
            loadUserDashboard();
        } catch (err) {
            showToast(err.message || "Failed to delete.", "error");
        }
    }

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------
    function openModal(modal) {
        if (modal) modal.classList.add("active");
    }

    function closeModal(modal) {
        if (modal) modal.classList.remove("active");
    }

    function showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span>${escapeHtml(message)}</span>`;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(20px)";
            setTimeout(() => toast.remove(), 250);
        }, 4000);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Startup
    document.addEventListener("DOMContentLoaded", init);

    return {
        showToast,
        openLoginModal: () => openModal(document.getElementById("loginModal")),
        loadUserDashboard,
        deleteBudget,
        deleteSavingsGoal,
        deleteLoan,
    };
})();
