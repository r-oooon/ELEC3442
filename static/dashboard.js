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

  // Show the last 10 activities, most recent at the top
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
    // Fetch from both endpoints simultaneously to reduce latency
    const [statsRes, realtimeRes] = await Promise.all([
      fetch('/api/stats'),
      fetch('/api/realtime_stats')
    ]);
    
    if (!statsRes.ok || !realtimeRes.ok) {
      throw new Error('API request failed');
    }

    const stats = await statsRes.json();
    const realtime = await realtimeRes.json();

    // 1. Update Phase and Counter
    renderPhase(realtime.current_phase || stats.latest_state || 'UNKNOWN');
    totalPresses.textContent = stats.total_presses ?? 0;
    
    // 2. Update Connection Status
    statusBadge.textContent = '● Live';
    statusBadge.style.backgroundColor = '#047857';

    // 3. Update Chart Data (Memory Leak Fix: Only update data, don't recreate)
    const counts = stats.hourly_data?.map(point => point.count ?? 0) ?? Array(24).fill(0);
    if (window.hourlyChart) {
      window.hourlyChart.data.datasets[0].data = counts;
      // Use 'none' mode to skip animations for better performance at 1s intervals
      window.hourlyChart.update('none'); 
    }

    // 4. Update Recent Activity List
    renderRecentActivity(realtime.recent_activity ?? []);
    
  } catch (error) {
    statusBadge.textContent = '● Offline (Reconnecting...)';
    statusBadge.style.backgroundColor = '#991b1b';
    console.error('Dashboard load error:', error);
  }
}

function setupDashboardChart() {
  const canvas = document.getElementById('hourlyChart');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  
  // Ensure we don't create multiple charts if this function is called twice
  if (window.hourlyChart) {
    window.hourlyChart.destroy();
  }

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
      maintainAspectRatio: false, // Prevents the "growing height" issue
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
      },
      animation: {
        duration: 400 // Short animation for a smoother feel
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupDashboardChart();
  
  // Initial load
  loadStats();
  
  // Set interval to 1000ms (1 second) for real-time updates
  setInterval(loadStats, 1000);
});