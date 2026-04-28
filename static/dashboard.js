/**
 * dashboard.js — Logic for the Smart Pedestrian Crossing Dashboard.
 * Optimized for real-time updates and memory efficiency.
 */

function renderPhase(phase) {
  const currentPhase = document.getElementById('currentPhase');
  const phaseLabel = document.getElementById('phaseLabel');
  const normalized = phase || 'UNKNOWN';
  
  // Clean up the display text (e.g., VEHICLE_GREEN -> VEHICLE GREEN)
  currentPhase.textContent = normalized.replace(/_/g, ' ');
  phaseLabel.textContent = normalized;
  
  // Update the CSS class for the status pill
  phaseLabel.className = `status-pill state-${normalized}`;
}

function renderRecentActivity(timestamps) {
  const recentActivity = document.getElementById('recentActivity');
  recentActivity.innerHTML = '';
  if (!timestamps || !timestamps.length) {
    recentActivity.innerHTML = '<li class="list-item">No recent activity.</li>';
    return;
  }
  timestamps.slice(-10).reverse().forEach(ts => {
    const date = new Date(ts * 1000);
    const item = document.createElement('li');
    item.className = 'list-item';
    item.innerHTML = `<span>Button press recorded</span><time>${date.toLocaleTimeString()}</time>`;
    recentActivity.appendChild(item);
  });
}

async function loadStats() {
  const statusBadge = document.getElementById('statusBadge');
  const totalPresses = document.getElementById('totalPresses');

  try {
    const [statsRes, realtimeRes] = await Promise.all([
      fetch('/api/stats'),
      fetch('/api/realtime_stats')
    ]);
    if (!statsRes.ok || !realtimeRes.ok) {
      throw new Error('API request failed');
    }

    const stats = await statsRes.json();
    const realtime = await realtimeRes.json();

    renderPhase(realtime.current_phase || stats.latest_state || 'UNKNOWN');
    totalPresses.textContent = stats.total_presses ?? 0;
    statusBadge.textContent = '● Live';
    statusBadge.style.backgroundColor = '#047857';

    // const counts = stats.hourly_data?.map(point => point.count ?? 0) ?? Array(24).fill(0);
    // if (window.hourlyChart) {
    //   window.hourlyChart.data.datasets[0].data = counts;
    //   window.hourlyChart.update();

    // 1. Update existing Hourly Chart
    updateChart(window.hourlyChart, stats.hourly_data.map(d => d.count));

    // 2. Client-side Analytics: Wait Time Histogram
    const waitData = calculateWaitHistogram(stats.raw_presses || []);
    updateChart(window.waitChart, waitData.data, waitData.labels);

    // 3. Client-side Analytics: Phase Durations
    const phaseData = calculatePhaseAverages(stats.raw_phases || []);
    updateChart(window.phaseChart, phaseData.data, phaseData.labels);
    renderRecentActivity(realtime.recent_activity ?? []);
  } catch (error) {
    statusBadge.textContent = '● Offline (Reconnecting...)';
    statusBadge.style.backgroundColor = '#991b1b';
    console.error('Dashboard load error:', error);
  }
}

    function updateChart(chart, newData, newLabels = null) {
    if (!chart) return;
    chart.data.datasets[0].data = newData;
    if (newLabels) chart.data.labels = newLabels;
    chart.update('none'); // 'none' prevents animation frame lag during rapid updates
  }

// Initialize charts on DOMContentLoaded...
function setupAnalyticsCharts() {
  // Initialize waitChart and phaseChart using standard Chart.js constructor
  // 1. Wait Time Histogram
  const waitCtx = document.getElementById('waitHistogram').getContext('2d');
  window.waitChart = new Chart(waitCtx, {
    type: 'bar',
    data: {
      labels: ["0-5s", "5-10s", "10-15s", "15-20s", "20-30s", "30s+"],
      datasets: [{
        label: 'Number of Pedestrians',
        data: [],
        backgroundColor: 'rgba(249, 115, 22, 0.8)', // Orange theme
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, ticks: { color: '#9ca3af' }, grid: { color: '#374151' } },
        x: { ticks: { color: '#9ca3af' }, grid: { display: false } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // 2. Average Phase Duration Chart
  const phaseCtx = document.getElementById('phaseAvgChart').getContext('2d');
  window.phaseChart = new Chart(phaseCtx, {
    type: 'bar',
    data: {
      labels: [],
      datasets: [{
        label: 'Avg Duration (sec)',
        data: [],
        backgroundColor: 'rgba(16, 185, 129, 0.8)', // Green theme
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y', // Makes it a horizontal bar chart like analytics.py
      scales: {
        x: { beginAtZero: true, ticks: { color: '#9ca3af' }, grid: { color: '#374151' } },
        y: { ticks: { color: '#9ca3af' }, grid: { display: false } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function setupDashboardChart() {
  const ctx = document.getElementById('hourlyChart').getContext('2d');
  window.hourlyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
      datasets: [{
        label: 'Button presses',
        data: Array(24).fill(0),
        backgroundColor: 'rgba(59, 130, 246, 0.85)',
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false }, ticks: { color: '#d1d5db' } },
        y: { 
            beginAtZero: true, 
            ticks: { color: '#d1d5db', stepSize: 1 }, 
            grid: { color: 'rgba(255,255,255,0.08)' } 
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      }
    }
  });
}

function calculateWaitHistogram(presses) {
    const bins = ["0-5s", "5-10s", "10-15s", "15-20s", "20-30s", "30s+"];
    const counts = new Array(bins.length).fill(0);

    presses.forEach(p => {
        const w = p.wait_time || 0;
        if (w < 5) counts[0]++;
        else if (w < 10) counts[1]++;
        else if (w < 15) counts[2]++;
        else if (w < 20) counts[3]++;
        else if (w < 30) counts[4]++;
        else counts[5]++;
    });
    return { labels: bins, data: counts };
}

function calculatePhaseAverages(phases) {
    const totals = {}; // { phaseName: { sum: 0, count: 0 } }

    phases.forEach(p => {
        if (!totals[p.phase]) totals[p.phase] = { sum: 0, count: 0 };
        totals[p.phase].sum += p.duration || 0;
        totals[p.phase].count += 1;
    });

    const labels = Object.keys(totals);
    const averages = labels.map(l => (totals[l].sum / totals[l].count).toFixed(1));
    return { labels, data: averages };
}

document.addEventListener('DOMContentLoaded', () => {
  setupDashboardChart();
  setupAnalyticsCharts();
  loadStats();
  setInterval(loadStats, 3000);
});