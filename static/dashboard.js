function renderPhase(phase) {
  const currentPhase = document.getElementById('currentPhase');
  const phaseLabel = document.getElementById('phaseLabel');
  const normalized = phase || 'UNKNOWN';
  currentPhase.textContent = normalized;
  phaseLabel.textContent = normalized;
  phaseLabel.className = `status-pill state-${normalized}`;
}

function renderRecentActivity(timestamps) {
  const recentActivity = document.getElementById('recentActivity');
  recentActivity.innerHTML = '';
  if (!timestamps.length) {
    recentActivity.innerHTML = '<li class="list-item">No recent activity.</li>';
    return;
  }
  timestamps.slice().reverse().forEach(ts => {
    const date = new Date(ts * 1000);
    const item = document.createElement('li');
    item.className = 'list-item';
    item.innerHTML = `<span>Button press recorded</span><time>${date.toLocaleString()}</time>`;
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
    statusBadge.textContent = 'Live';
    statusBadge.style.backgroundColor = '#047857';

    const counts = stats.hourly_data?.map(point => point.count ?? 0) ?? Array(24).fill(0);
    if (window.hourlyChart) {
      window.hourlyChart.data.datasets[0].data = counts;
      window.hourlyChart.update();
    }

    renderRecentActivity(realtime.recent_activity ?? []);
  } catch (error) {
    statusBadge.textContent = 'Offline';
    statusBadge.style.backgroundColor = '#991b1b';
    console.error('Dashboard load error:', error);
  }
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
        y: { beginAtZero: true, ticks: { color: '#d1d5db' }, grid: { color: 'rgba(255,255,255,0.08)' } }
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupDashboardChart();
  loadStats();
  setInterval(loadStats, 5000);
});
