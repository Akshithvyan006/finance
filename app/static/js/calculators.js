/**
 * Financial Calculators Module
 * Interactive math, Chart.js live visualizers, and saved scenario management.
 */

const Calculators = (() => {
    let budgetChartInstance = null;
    let savingsChartInstance = null;
    let loanChartInstance = null;

    function init() {
        initSubtabs();
        initBudgetCalc();
        initSavingsCalc();
        initLoanCalc();

        // Run default calculations on initial load
        calculateBudget();
        calculateSavings();
        calculateLoan();
    }

    function initSubtabs() {
        const subtabs = document.querySelectorAll(".calc-subtab");
        subtabs.forEach(tab => {
            tab.addEventListener("click", () => {
                subtabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");

                const targetId = tab.dataset.calc;
                document.querySelectorAll(".calc-content").forEach(c => c.classList.remove("active"));
                const target = document.getElementById(targetId);
                if (target) target.classList.add("active");
            });
        });
    }

    // -------------------------------------------------------------------------
    // 1. Budget Calculator
    // -------------------------------------------------------------------------
    function initBudgetCalc() {
        document.getElementById("runBudgetCalcBtn")?.addEventListener("click", calculateBudget);
        document.getElementById("saveBudgetBtn")?.addEventListener("click", saveBudget);
    }

    async function calculateBudget() {
        const income = parseFloat(document.getElementById("budgetIncome")?.value || 5000);
        const needsPct = parseFloat(document.getElementById("budgetNeedsPct")?.value || 50);
        const wantsPct = parseFloat(document.getElementById("budgetWantsPct")?.value || 30);
        const savingsPct = parseFloat(document.getElementById("budgetSavingsPct")?.value || 20);

        try {
            const data = await Api.post("/api/v1/calculators/budget", {
                monthly_income: income,
                needs_pct: needsPct,
                wants_pct: wantsPct,
                savings_pct: savingsPct,
            });

            document.getElementById("metricNeeds").textContent = `$${data.allocations.needs.toLocaleString()}`;
            document.getElementById("metricWants").textContent = `$${data.allocations.wants.toLocaleString()}`;
            document.getElementById("metricSavings").textContent = `$${data.allocations.savings.toLocaleString()}`;
            document.getElementById("metricEmergencyTarget").textContent = `$${data.summary.emergency_fund_target_6mo.toLocaleString()}`;

            renderBudgetChart(data.allocations);
        } catch (err) {
            console.error("Budget calc error:", err);
        }
    }

    function renderBudgetChart(allocations) {
        const ctx = document.getElementById("budgetChart")?.getContext("2d");
        if (!ctx) return;

        if (budgetChartInstance) budgetChartInstance.destroy();

        budgetChartInstance = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Needs (50%)", "Wants (30%)", "Savings (20%)"],
                datasets: [{
                    data: [allocations.needs, allocations.wants, allocations.savings],
                    backgroundColor: ["#6366f1", "#f59e0b", "#10b981"],
                    borderWidth: 2,
                    borderColor: "#111827",
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { color: "#9ca3af" } }
                }
            }
        });
    }

    async function saveBudget() {
        if (!Api.getToken()) {
            window.App?.showToast("Sign in to save budget scenarios to your profile.", "info");
            return;
        }

        const income = parseFloat(document.getElementById("budgetIncome")?.value || 5000);
        const needs = parseFloat(document.getElementById("metricNeeds")?.textContent.replace(/[^0-9.-]+/g, "") || 2500);
        const wants = parseFloat(document.getElementById("metricWants")?.textContent.replace(/[^0-9.-]+/g, "") || 1500);
        const savings = parseFloat(document.getElementById("metricSavings")?.textContent.replace(/[^0-9.-]+/g, "") || 1000);
        const notes = document.getElementById("budgetNotes")?.value || "Personal Budget Plan";

        try {
            await Api.post("/api/v1/user/budgets", {
                monthly_income: income,
                needs_amount: needs,
                wants_amount: wants,
                savings_amount: savings,
                notes: notes,
            });
            window.App?.showToast("Budget plan successfully saved to your profile!", "success");
            window.App?.loadUserDashboard();
        } catch (err) {
            window.App?.showToast(err.message || "Failed to save budget.", "error");
        }
    }

    // -------------------------------------------------------------------------
    // 2. Savings & Compound Calculator
    // -------------------------------------------------------------------------
    function initSavingsCalc() {
        document.getElementById("runSavingsCalcBtn")?.addEventListener("click", calculateSavings);
        document.getElementById("saveSavingsBtn")?.addEventListener("click", saveSavingsGoal);
    }

    async function calculateSavings() {
        const initial = parseFloat(document.getElementById("savingsInitial")?.value || 5000);
        const monthly = parseFloat(document.getElementById("savingsMonthly")?.value || 400);
        const rate = parseFloat(document.getElementById("savingsRate")?.value || 6.5);
        const years = parseInt(document.getElementById("savingsYears")?.value || 10);

        try {
            const data = await Api.post("/api/v1/calculators/savings", {
                initial_deposit: initial,
                monthly_contribution: monthly,
                annual_rate_pct: rate,
                years: years,
            });

            document.getElementById("metricFutureValue").textContent = `$${data.results.future_value.toLocaleString()}`;
            document.getElementById("metricTotalPrincipal").textContent = `$${data.results.total_principal.toLocaleString()}`;
            document.getElementById("metricTotalInterest").textContent = `$${data.results.total_interest_earned.toLocaleString()}`;

            renderSavingsChart(data.trajectory);
        } catch (err) {
            console.error("Savings calc error:", err);
        }
    }

    function renderSavingsChart(trajectory) {
        const ctx = document.getElementById("savingsChart")?.getContext("2d");
        if (!ctx) return;

        if (savingsChartInstance) savingsChartInstance.destroy();

        const labels = trajectory.map(t => `Year ${t.year}`);
        const principalData = trajectory.map(t => t.principal_invested);
        const totalData = trajectory.map(t => t.total_balance);

        savingsChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Total Balance",
                        data: totalData,
                        borderColor: "#10b981",
                        backgroundColor: "rgba(16, 185, 129, 0.15)",
                        fill: true,
                        tension: 0.3,
                    },
                    {
                        label: "Principal Invested",
                        data: principalData,
                        borderColor: "#6366f1",
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.1,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(255,255,255,0.05)" } },
                    y: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(255,255,255,0.05)" } }
                },
                plugins: {
                    legend: { labels: { color: "#9ca3af" } }
                }
            }
        });
    }

    async function saveSavingsGoal() {
        if (!Api.getToken()) {
            window.App?.showToast("Sign in to save savings goals.", "info");
            return;
        }

        const title = document.getElementById("savingsGoalTitle")?.value || "Compound Growth Goal";
        const initial = parseFloat(document.getElementById("savingsInitial")?.value || 5000);
        const monthly = parseFloat(document.getElementById("savingsMonthly")?.value || 400);
        const rate = parseFloat(document.getElementById("savingsRate")?.value || 6.5);
        const years = parseInt(document.getElementById("savingsYears")?.value || 10);
        const futureVal = parseFloat(document.getElementById("metricFutureValue")?.textContent.replace(/[^0-9.-]+/g, "") || 0);
        const interest = parseFloat(document.getElementById("metricTotalInterest")?.textContent.replace(/[^0-9.-]+/g, "") || 0);

        try {
            await Api.post("/api/v1/user/savings-goals", {
                title,
                target_amount: futureVal,
                initial_deposit: initial,
                monthly_contribution: monthly,
                annual_interest_rate: rate,
                time_horizon_years: years,
                projected_total: futureVal,
                total_interest_earned: interest,
            });
            window.App?.showToast("Savings goal saved successfully!", "success");
            window.App?.loadUserDashboard();
        } catch (err) {
            window.App?.showToast(err.message || "Failed to save goal.", "error");
        }
    }

    // -------------------------------------------------------------------------
    // 3. Loan Amortization Calculator
    // -------------------------------------------------------------------------
    function initLoanCalc() {
        document.getElementById("runLoanCalcBtn")?.addEventListener("click", calculateLoan);
        document.getElementById("saveLoanBtn")?.addEventListener("click", saveLoanScenario);
    }

    async function calculateLoan() {
        const principal = parseFloat(document.getElementById("loanPrincipal")?.value || 25000);
        const rate = parseFloat(document.getElementById("loanRate")?.value || 6.2);
        const term = parseInt(document.getElementById("loanTermMonths")?.value || 60);

        try {
            const data = await Api.post("/api/v1/calculators/loan", {
                principal,
                annual_rate_pct: rate,
                term_months: term,
            });

            document.getElementById("metricMonthlyPayment").textContent = `$${data.results.monthly_payment.toLocaleString()}`;
            document.getElementById("metricLoanInterest").textContent = `$${data.results.total_interest.toLocaleString()}`;
            document.getElementById("metricLoanTotal").textContent = `$${data.results.total_cost.toLocaleString()}`;

            renderLoanChart(principal, data.results.total_interest);
        } catch (err) {
            console.error("Loan calc error:", err);
        }
    }

    function renderLoanChart(principal, interest) {
        const ctx = document.getElementById("loanChart")?.getContext("2d");
        if (!ctx) return;

        if (loanChartInstance) loanChartInstance.destroy();

        loanChartInstance = new Chart(ctx, {
            type: "pie",
            data: {
                labels: ["Principal Borrowed", "Total Interest Cost"],
                datasets: [{
                    data: [principal, interest],
                    backgroundColor: ["#3b82f6", "#ef4444"],
                    borderWidth: 2,
                    borderColor: "#111827",
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { color: "#9ca3af" } }
                }
            }
        });
    }

    async function saveLoanScenario() {
        if (!Api.getToken()) {
            window.App?.showToast("Sign in to save loan scenarios.", "info");
            return;
        }

        const name = document.getElementById("loanNameInput")?.value || "Tracked Loan";
        const principal = parseFloat(document.getElementById("loanPrincipal")?.value || 25000);
        const rate = parseFloat(document.getElementById("loanRate")?.value || 6.2);
        const term = parseInt(document.getElementById("loanTermMonths")?.value || 60);
        const monthly = parseFloat(document.getElementById("metricMonthlyPayment")?.textContent.replace(/[^0-9.-]+/g, "") || 0);
        const interest = parseFloat(document.getElementById("metricLoanInterest")?.textContent.replace(/[^0-9.-]+/g, "") || 0);
        const total = parseFloat(document.getElementById("metricLoanTotal")?.textContent.replace(/[^0-9.-]+/g, "") || 0);

        try {
            await Api.post("/api/v1/user/loans", {
                loan_name: name,
                principal,
                annual_rate: rate,
                term_months: term,
                monthly_payment: monthly,
                total_interest: interest,
                total_cost: total,
            });
            window.App?.showToast("Loan scenario saved successfully!", "success");
            window.App?.loadUserDashboard();
        } catch (err) {
            window.App?.showToast(err.message || "Failed to save loan scenario.", "error");
        }
    }

    return {
        init,
        calculateBudget,
        calculateSavings,
        calculateLoan,
    };
})();
