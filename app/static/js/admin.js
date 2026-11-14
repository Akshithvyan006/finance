/**
 * Admin Module
 * User administration, RBAC role assignment, audit log inspection, and security telemetry.
 */

const Admin = (() => {
    function init() {
        document.getElementById("refreshUsersBtn")?.addEventListener("click", loadUsers);
        document.getElementById("refreshAuditBtn")?.addEventListener("click", loadAuditLogs);
    }

    async function loadAdminWorkspace() {
        await Promise.all([
            loadSystemStats(),
            loadUsers(),
            loadAuditLogs(),
        ]);
    }

    async function loadSystemStats() {
        try {
            const data = await Api.get("/api/v1/admin/system-stats");
            document.getElementById("adminTotalUsers").textContent = data.users.total;
            document.getElementById("adminTotalAudits").textContent = data.security.total_audit_events;
            document.getElementById("adminFailedLogins").textContent = data.security.failed_logins_recorded;
            document.getElementById("adminSecurityAlerts").textContent = data.security.security_violations_flagged;
        } catch (err) {
            console.error("Failed to load admin system stats:", err);
        }
    }

    async function loadUsers() {
        const tbody = document.querySelector("#adminUsersTable tbody");
        if (!tbody) return;

        try {
            const data = await Api.get("/api/v1/admin/users");
            const currentUserId = Api.getUser()?.id;

            if (!data.users || data.users.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No users found.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.users.map(u => {
                const isSelf = u.id === currentUserId;
                const statusBadge = u.is_active
                    ? `<span class="badge" style="color:var(--success); font-weight:600;">Active</span>`
                    : `<span class="badge" style="color:var(--danger); font-weight:600;">Deactivated</span>`;

                return `
                    <tr>
                        <td>#${u.id}</td>
                        <td><strong>${escapeHtml(u.username)}</strong> ${isSelf ? "(You)" : ""}</td>
                        <td>${escapeHtml(u.email)}</td>
                        <td>
                            <select class="role-select" data-user-id="${u.id}" ${isSelf ? "disabled title='Self-demotion prohibited'" : ""}>
                                <option value="User" ${u.role === "User" ? "selected" : ""}>User</option>
                                <option value="Financial Analyst" ${u.role === "Financial Analyst" ? "selected" : ""}>Financial Analyst</option>
                                <option value="Admin" ${u.role === "Admin" ? "selected" : ""}>Admin</option>
                            </select>
                        </td>
                        <td>${statusBadge}</td>
                        <td>${u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}</td>
                        <td>
                            ${!isSelf ? `
                                <button class="btn btn-sm ${u.is_active ? "btn-delete" : "btn-secondary"}" 
                                        onclick="Admin.toggleStatus(${u.id}, ${!u.is_active})">
                                    ${u.is_active ? "Deactivate" : "Activate"}
                                </button>
                            ` : `<span class="text-muted" style="font-size:0.75rem;">Protected</span>`}
                        </td>
                    </tr>
                `;
            }).join("");

            // Add change listener to role selects
            tbody.querySelectorAll(".role-select").forEach(select => {
                select.addEventListener("change", async (e) => {
                    const userId = e.target.dataset.userId;
                    const newRole = e.target.value;
                    await updateUserRole(userId, newRole);
                });
            });

        } catch (err) {
            console.error("Failed to load users:", err);
            if (err.status === 403) {
                window.App?.showToast("Forbidden: Administrator privileges required.", "error");
            }
        }
    }

    async function updateUserRole(userId, newRole) {
        try {
            const res = await Api.put(`/api/v1/admin/users/${userId}/role`, { role: newRole });
            window.App?.showToast(res.message || "User role updated successfully.", "success");
            await loadSystemStats();
            await loadAuditLogs();
        } catch (err) {
            window.App?.showToast(err.message || "Failed to update role.", "error");
            await loadUsers(); // Revert select on failure
        }
    }

    async function toggleStatus(userId, shouldActivate) {
        try {
            const res = await Api.put(`/api/v1/admin/users/${userId}/status`, { is_active: shouldActivate });
            window.App?.showToast(res.message, "success");
            await loadUsers();
            await loadSystemStats();
            await loadAuditLogs();
        } catch (err) {
            window.App?.showToast(err.message || "Failed to update user status.", "error");
        }
    }

    async function loadAuditLogs() {
        const tbody = document.querySelector("#auditLogsTable tbody");
        if (!tbody) return;

        const actionFilter = document.getElementById("auditFilterAction")?.value || "";
        const statusFilter = document.getElementById("auditFilterStatus")?.value || "";

        let url = "/api/v1/admin/audit-logs?limit=50";
        if (actionFilter) url += `&action=${encodeURIComponent(actionFilter)}`;
        if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;

        try {
            const data = await Api.get(url);
            if (!data.audit_logs || data.audit_logs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No audit logs matching criteria.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.audit_logs.map(log => {
                let statusClass = "text-muted";
                if (log.status === "SUCCESS") statusClass = "text-success";
                if (log.status === "DENIED") statusClass = "text-danger";
                if (log.status === "WARNING") statusClass = "text-warning";

                return `
                    <tr>
                        <td style="font-family:var(--font-mono); font-size:0.75rem;">
                            ${log.timestamp ? new Date(log.timestamp).toLocaleString() : "-"}
                        </td>
                        <td><strong>${escapeHtml(log.username || "Anonymous")}</strong></td>
                        <td style="font-family:var(--font-mono); font-size:0.75rem;">${escapeHtml(log.ip_address)}</td>
                        <td><code>${escapeHtml(log.action)}</code></td>
                        <td>${escapeHtml(log.resource)}</td>
                        <td><span class="${statusClass}"><strong>${escapeHtml(log.status)}</strong></span></td>
                        <td style="font-size:0.75rem; color:var(--text-secondary); max-width:280px; word-break:break-word;">
                            ${escapeHtml(log.details || "-")}
                        </td>
                    </tr>
                `;
            }).join("");
        } catch (err) {
            console.error("Failed to load audit logs:", err);
        }
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

    return {
        init,
        loadAdminWorkspace,
        toggleStatus,
    };
})();
