/**
 * Financial Analyst Module
 * Authorized datasets visualization, macroeconomic stress testing, and Monte Carlo stochastic projections.
 */

const Analyst = (() => {
    let macroChartInstance = null;
    let monteCarloChartInstance = null;

    function init() {
        document.getElementById("runStressTestBtn")?.addEventListener("click", runStressTest);
        document.getElementById("runMonteCarloBtn")?.addEventListener("click", runMonteCarlo);
    }

    async function loadAnalystWorkspace() {
        await loadMacroDatasets();
        await runStressTest();
        await runMonteCarlo();
    }

    async function loadMacroDatasets() {
        try {
            const data = await Api.get("/api/v1/analyst/datasets");
            const macroDs = data.authorized_datasets.find(d => d.dataset_code === "MACRO_INFLATION_BENCHMARK_2015_2024");
            if (macroDs && macroDs.data) {
                renderMacroChart(macroDs.data);
            }
        } catch (err) {
            console.error("Failed to load macro datasets:", err);
            if (err.status === 403) {
                window.App?.showToast("Forbidden: Access to Analyst datasets requires Financial Analyst role.", "error");
            }
        }
    }

    function renderMacroChart(dataset) {
        const ctx = document.getElementById("macroChart")?.getContext("2d");
        if (!ctx) return;

        if (macroChartInstance) macroChartInstance.destroy();

        macroChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: dataset.years,
                datasets: [
                    {
                        label: "Headline CPI Inflation (%)",
                        data: dataset.cpi_inflation_pct,
                        borderColor: "#ef4444",
                        backgroundColor: "rgba(239, 68, 68, 0.1)",
                        borderWidth: 2,
                        tension: 0.2,
                    },
                    {
                        label: "10-Year Treasury Yield (%)",
                        data: dataset.us_10yr_treasury_yield_pct,
                        borderColor: "#3b82f6",
                        borderWidth: 2,
                        tension: 0.2,
                    },
                    {
                        label: "S&P 500 Annual Return (%)",
                        data: dataset.sp500_annual_return_pct,
                        borderColor: "#10b981",
                        borderWidth: 2,
                        borderDash: [4, 4],
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
                    legend: { labels: { color: "#9ca3af" } },
                    tooltip: { mode: "index", intersect: false }
                }
            }
        });
    }

    async function runStressTest() {
        const equity = parseFloat(document.getElementById("stressEquity")?.value || 60);
        const bond = parseFloat(document.getElementById("stressBond")?.value || 30);
        const cash = parseFloat(document.getElementById("stressCash")?.value || 10);
        const infShock = parseFloat(document.getElementById("stressInfBps")?.value || 250);
        const rateShock = parseFloat(document.getElementById("stressRateBps")?.value || 200);

        try {
            const data = await Api.post("/api/v1/analyst/stress-test", {
                equity_pct: equity,
                bond_pct: bond,
                cash_pct: cash,
                inflation_shock_bps: infShock,
                interest_rate_hike_bps: rateShock,
            });

            const resContainer = document.getElementById("stressResultsContainer");
            if (resContainer) resContainer.style.display = "grid";

            const netImpactEl = document.getElementById("stressNetImpact");
            const ratingEl = document.getElementById("stressRiskRating");

            if (netImpactEl) {
                const impact = data.simulated_impact.net_portfolio_impact_pct;
                netImpactEl.textContent = `${impact >= 0 ? "+" : ""}${impact}%`;
                netImpactEl.className = `metric-val ${impact < 0 ? "text-danger" : "text-success"}`;
            }

            if (ratingEl) {
                ratingEl.textContent = data.simulated_impact.risk_rating;
            }

            window.App?.showToast("Macro stress test completed.", "success");
        } catch (err) {
            console.error("Stress test error:", err);
            window.App?.showToast(err.message || "Stress test failed.", "error");
        }
    }

    async function runMonteCarlo() {
        const initial = parseFloat(document.getElementById("mcInitial")?.value || 20000);
        const monthly = parseFloat(document.getElementById("mcMonthly")?.value || 600);
        const mean = parseFloat(document.getElementById("mcMean")?.value || 8.0);
        const vol = parseFloat(document.getElementById("mcVol")?.value || 16.0);
        const years = parseInt(document.getElementById("mcYears")?.value || 10);

        try {
            const data = await Api.post("/api/v1/analyst/monte-carlo", {
                initial_balance: initial,
                monthly_deposit: monthly,
                annual_mean_return_pct: mean,
                annual_volatility_pct: vol,
                years: years,
                num_simulations: 300,
            });

            renderMonteCarloChart(data.yearly_trajectory);
            window.App?.showToast("Monte Carlo 300-run simulation completed.", "success");
        } catch (err) {
            console.error("Monte Carlo error:", err);
            window.App?.showToast(err.message || "Monte Carlo simulation failed.", "error");
        }
    }

    function renderMonteCarloChart(trajectory) {
        const ctx = document.getElementById("monteCarloChart")?.getContext("2d");
        if (!ctx) return;

        if (monteCarloChartInstance) monteCarloChartInstance.destroy();

        const labels = trajectory.map(t => `Yr ${t.year}`);
        const p10 = trajectory.map(t => t.percentile_10_bear);
        const p50 = trajectory.map(t => t.percentile_50_median);
        const p90 = trajectory.map(t => t.percentile_90_bull);

        monteCarloChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "90th Percentile (Bull Case)",
                        data: p90,
                        borderColor: "#10b981",
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                    },
                    {
                        label: "50th Percentile (Median Projection)",
                        data: p50,
                        borderColor: "#6366f1",
                        backgroundColor: "rgba(99, 102, 241, 0.15)",
                        borderWidth: 3,
                        fill: "-1",
                        tension: 0.3,
                    },
                    {
                        label: "10th Percentile (Bear Case)",
                        data: p10,
                        borderColor: "#f59e0b",
                        borderWidth: 2,
                        fill: "-1",
                        tension: 0.3,
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

    return {
        init,
        loadAnalystWorkspace,
    };
})();
