const appState = {
    scenarios: {},
    lastResult: null,
    charts: {}
};

const formatNumber = (value, suffix = 'kW') => `${Number(value || 0).toFixed(1)} ${suffix}`;

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Request failed');
    }
    return data;
}

function bindNavigation() {
    document.querySelectorAll('.nav-link').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.nav-link').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
            button.classList.add('active');
            const pageId = button.dataset.target;
            document.getElementById(pageId).classList.add('active');
        });
    });
}

async function loadScenarios() {
    const data = await fetchJson('/api/scenarios');
    appState.scenarios = data.scenarios || {};
    const select = document.getElementById('scenario-select');
    const options = Object.entries(appState.scenarios).map(([key, value]) => `<option value="${key}">${value.scenario_name}</option>`).join('');
    select.innerHTML = options;
}

async function simulateScenario() {
    const scenarioName = document.getElementById('scenario-select').value;
    const payload = {
        scenario_name: scenarioName,
        custom_overrides: {
            grid_availability_kw: Number(document.getElementById('grid-availability').value || 0),
            solar_generation_kw: Number(document.getElementById('solar-generation').value || 0),
            battery_soc_percent: Number(document.getElementById('battery-soc-input').value || 0),
            demand_multiplier: Number(document.getElementById('demand-multiplier').value || 1),
            generator_available: document.getElementById('generator-available').checked,
        },
    };

    try {
        const data = await fetchJson('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        appState.lastResult = data;
        renderDashboard(data);
        renderRecovery(data);
        renderAgents(data);
        renderAnalytics(data);
        renderGridStatus(data);
        renderHistory();
    } catch (error) {
        alert(error.message);
    }
}

async function loadHistory() {
    try {
        const data = await fetchJson('/api/simulations');
        const rows = data.simulations || [];
        const historyTable = document.getElementById('history-table');
        historyTable.innerHTML = rows.slice(0, 8).map(sim => `
            <tr>
                <td>${sim.id}</td>
                <td>${sim.scenario_name}</td>
                <td>${JSON.parse(sim.summary || '{}').status || 'ok'}</td>
                <td><button data-id="${sim.id}" class="open-report">Open</button></td>
            </tr>
        `).join('');

        historyTable.querySelectorAll('.open-report').forEach(button => {
            button.addEventListener('click', async () => {
                const response = await fetch(`/api/simulation/${button.dataset.id}/report`);
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                window.open(url, '_blank');
            });
        });
    } catch (error) {
        console.error(error);
    }
}

async function renderHistory() {
    await loadHistory();
}

async function resetHistory() {
    await fetch('/api/reset', { method: 'POST' });
    await loadHistory();
}

function renderDashboard(data) {
    const diagnosis = data.diagnosis || {};
    const resource = data.resource_analysis?.resources || {};
    document.getElementById('system-health').textContent = diagnosis.severity || 'Stable';
    document.getElementById('total-demand').textContent = formatNumber(data.initial_demand_kw || 0, 'kW');
    document.getElementById('available-power').textContent = formatNumber(data.available_supply_kw || 0, 'kW');
    document.getElementById('battery-soc').textContent = `${resource.battery_soc_percent || 0}%`;
    document.getElementById('system-summary').innerHTML = `
        <li>Scenario: ${data.scenario_name}</li>
        <li>Incident: ${diagnosis.incident || 'Normal'}</li>
        <li>Battery discharge: ${resource.battery_kw || 0} kW</li>
        <li>Generator: ${resource.generator_kw || 0} kW</li>
    `;
    const recent = document.getElementById('recent-simulations');
    recent.innerHTML = `<li>Current run: ${data.scenario_name}</li><li>Recommendation: ${data.recommended_strategy?.strategy_name || 'Pending'}</li>`;
}

function renderAgents(data) {
    const container = document.getElementById('agent-logs');
    const logs = data.logs || [];
    container.innerHTML = logs.map(log => `
        <div class="agent-item ${log.status === 'Warning' ? 'warning' : ''}">
            <strong>${log.agent_name}</strong>
            <div>${log.action}</div>
            <small>${log.output_summary}</small>
        </div>
    `).join('');
}

function renderGridStatus(data) {
    const svg = document.getElementById('microgrid-svg');
    const status = data.recommended_strategy ? data.recommended_strategy.validation?.status : 'Valid';
    const color = status === 'Valid' ? '#3ad17a' : '#f5a623';
    svg.querySelectorAll('rect').forEach((rect, idx) => {
        if (idx < 6 || idx === 6) {
            rect.setAttribute('fill', color);
        }
    });
}

function renderRecovery(data) {
    const container = document.getElementById('recovery-cards');
    const strategies = data.strategies || [];
    const recommended = data.recommended_strategy || strategies[0];
    container.innerHTML = strategies.map(strategy => `
        <div class="strategy-card ${strategy.strategy_name === recommended.strategy_name ? 'recommended' : ''}">
            <h4>${strategy.strategy_name}</h4>
            <ul>
                <li>Score: ${strategy.score}</li>
                <li>Allocated: ${strategy.allocated_kw} kW</li>
                <li>Unmet: ${strategy.unmet_demand_kw} kW</li>
                <li>Battery discharge: ${strategy.battery_discharge_kw} kW</li>
                <li>Validation: ${strategy.validation?.status || 'Unknown'}</li>
            </ul>
        </div>
    `).join('');
}

function renderAnalytics(data) {
    const strategyData = data.strategies || [];
    const labels = strategyData.map(s => s.strategy_name);
    const scores = strategyData.map(s => s.score || 0);
    const unserved = strategyData.map(s => s.unmet_demand_kw || 0);

    if (window.chartInstances) {
        window.chartInstances.forEach(chart => chart.destroy());
    }
    window.chartInstances = [];

    const demandCtx = document.getElementById('demandChart');
    window.chartInstances.push(new Chart(demandCtx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Recovery score',
                data: scores,
                backgroundColor: ['#3cc6ff', '#58d68d', '#f5a623']
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    }));

    const resourceCtx = document.getElementById('resourceChart');
    window.chartInstances.push(new Chart(resourceCtx, {
        type: 'doughnut',
        data: {
            labels: ['Grid', 'Solar', 'Battery', 'Generator'],
            datasets: [{
                data: [
                    data.resource_analysis?.resources?.grid_kw || 0,
                    data.resource_analysis?.resources?.solar_kw || 0,
                    data.resource_analysis?.resources?.battery_kw || 0,
                    data.resource_analysis?.resources?.generator_kw || 0,
                ],
                backgroundColor: ['#2bc4ff', '#58d68d', '#f5a623', '#f75d5d']
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    }));

    const batteryCtx = document.getElementById('batteryChart');
    window.chartInstances.push(new Chart(batteryCtx, {
        type: 'line',
        data: {
            labels: ['Current'],
            datasets: [{
                label: 'Battery SOC',
                data: [data.resource_analysis?.resources?.battery_soc_percent || 0],
                borderColor: '#58d68d',
                fill: false,
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    }));

    const loadCtx = document.getElementById('loadChart');
    window.chartInstances.push(new Chart(loadCtx, {
        type: 'radar',
        data: {
            labels: labels.length ? labels : ['Strategy'],
            datasets: [{
                label: 'Unmet demand',
                data: unserved.length ? unserved : [0],
                backgroundColor: 'rgba(79, 204, 255, 0.2)',
                borderColor: '#3cc6ff'
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    }));
}

async function initialiseApp() {
    bindNavigation();
    await loadScenarios();
    await loadHistory();
    document.getElementById('simulate-btn').addEventListener('click', simulateScenario);
    document.getElementById('reset-btn').addEventListener('click', resetHistory);
    await simulateScenario();
}

initialiseApp();
