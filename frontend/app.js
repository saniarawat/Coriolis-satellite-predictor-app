/**
 * Satellites Over My City - Frontend Application
 */

const API_BASE = 'http://localhost:5001/api';

let map = null;
let cityMarker = null;
let trackPolyline = null;
let satelliteMarker = null;
let animationInterval = null;
let passesPerDayChart = null;
let orbitChart = null;
let topSatellitesChart = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    checkHealth();
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    document.getElementById('city-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
});

function initMap() {
    map = L.map('map').setView([20.5937, 78.9629], 3);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
}

async function checkHealth() {
    const statusEl = document.getElementById('connection-status');
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        statusEl.className = 'status-indicator connected';
        statusEl.querySelector('.status-text').textContent = 'Backend connected';
    } catch {
        statusEl.className = 'status-indicator offline';
        statusEl.querySelector('.status-text').textContent = 'Backend offline';
    }
}

function hideError() {
    const banner = document.getElementById('error-banner');
    banner.classList.add('hidden');
    banner.textContent = '';
}

function showError(message) {
    const banner = document.getElementById('error-banner');
    banner.textContent = message;
    banner.classList.remove('hidden');
}

async function handleSearch() {
    const cityInput = document.getElementById('city-input');
    const city = cityInput.value.trim();
    if (!city) return;

    hideError();
    const spinner = document.getElementById('loading-spinner');
    spinner.classList.remove('hidden');

    try {
        const [passesRes, statsRes] = await Promise.all([
            fetch(`${API_BASE}/passes?city=${encodeURIComponent(city)}&hours=24`),
            fetch(`${API_BASE}/stats?city=${encodeURIComponent(city)}`)
        ]);

        const passesData = await passesRes.json();
        const statsData = await statsRes.json();

        if (!passesRes.ok) {
            if (passesData.error && passesData.error.toLowerCase().includes('not found')) {
                showError('City not found. Please try another name.');
            } else {
                showError(passesData.error || 'Failed to fetch passes');
            }
            return;
        }

        if (!statsRes.ok) {
            if (statsData.error && statsData.error.toLowerCase().includes('not found')) {
                showError('City not found. Please try another name.');
            }
        }

        populatePassTable(passesData.passes);
        drawGroundTrack(passesData);
        centerMapOnCity(passesData.lat, passesData.lon);
        updateCharts(statsData, city);
        document.querySelector('.pass-list-section').classList.add('fade-in');
    } catch (err) {
        showError('Could not connect to backend. Make sure it is running on port 5001.');
    } finally {
        spinner.classList.add('hidden');
    }
}

function populatePassTable(passes) {
    const tbody = document.getElementById('pass-table-body');
    tbody.innerHTML = '';

    if (!passes || passes.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No passes found for the next 24 hours</td></tr>';
        return;
    }

    passes.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(p.satellite_name)}</td>
            <td>${formatTime(p.rise_time)}</td>
            <td>${formatTime(p.peak_time)}</td>
            <td>${formatTime(p.set_time)}</td>
            <td>${p.max_elevation}°</td>
            <td>${p.duration_seconds}s</td>
        `;
        tbody.appendChild(tr);
    });
}

function formatTime(isoStr) {
    if (!isoStr) return '-';
    const d = new Date(isoStr);
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function drawGroundTrack(passesData) {
    if (animationInterval) {
        clearInterval(animationInterval);
        animationInterval = null;
    }

    if (trackPolyline) {
        map.removeLayer(trackPolyline);
        trackPolyline = null;
    }
    if (satelliteMarker) {
        map.removeLayer(satelliteMarker);
        satelliteMarker = null;
    }
    if (cityMarker) {
        map.removeLayer(cityMarker);
        cityMarker = null;
    }

    cityMarker = L.marker([passesData.lat, passesData.lon]).addTo(map);
    cityMarker.bindPopup(`<b>${escapeHtml(passesData.city)}</b>`);

    const firstPass = passesData.passes?.[0];
    if (!firstPass || !firstPass.ground_track || firstPass.ground_track.length === 0) {
        return;
    }

    const trackPoints = firstPass.ground_track.map(([lat, lon]) => [lat, lon]);
    trackPolyline = L.polyline(trackPoints, {
        color: '#00aaff',
        weight: 2,
        opacity: 0.8
    }).addTo(map);

    const satelliteIcon = L.divIcon({
        html: '<span style="font-size:20px">🛰</span>',
        className: 'satellite-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    satelliteMarker = L.marker(trackPoints[0], { icon: satelliteIcon }).addTo(map);

    let stepIndex = 0;
    const totalSteps = trackPoints.length;
    const stepInterval = 100;

    animationInterval = setInterval(() => {
        stepIndex = (stepIndex + 1) % totalSteps;
        const point = trackPoints[stepIndex];
        satelliteMarker.setLatLng(point);
    }, stepInterval);
}

function centerMapOnCity(lat, lon) {
    if (map && lat != null && lon != null) {
        map.setView([lat, lon], 6);
    }
}

function updateCharts(statsData, city) {
    const passesByDay = statsData.passes_by_day || [0, 0, 0, 0, 0, 0, 0];
    const orbitDist = statsData.orbit_type_distribution || { LEO: 0, MEO: 0, GEO: 0, OTHER: 0 };

    if (passesPerDayChart) passesPerDayChart.destroy();
    passesPerDayChart = new Chart(document.getElementById('passes-per-day-chart'), {
        type: 'bar',
        data: {
            labels: ['Today', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
            datasets: [{
                label: 'Passes',
                data: passesByDay,
                backgroundColor: 'rgba(0, 170, 255, 0.6)',
                borderColor: '#00aaff',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#a0b4c8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#a0b4c8' }
                }
            }
        }
    });

    if (orbitChart) orbitChart.destroy();
    orbitChart = new Chart(document.getElementById('orbit-chart'), {
        type: 'doughnut',
        data: {
            labels: ['LEO', 'MEO', 'GEO', 'OTHER'],
            datasets: [{
                data: [orbitDist.LEO, orbitDist.MEO, orbitDist.GEO, orbitDist.OTHER],
                backgroundColor: ['#00aaff', '#00cc66', '#ffaa00', '#a0b4c8'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#a0b4c8' }
                }
            }
        }
    });

    fetch(`${API_BASE}/passes/top?city=${encodeURIComponent(city)}`)
        .then(res => res.json())
        .then(data => {
            const top = data.top_satellites || [];
            if (topSatellitesChart) topSatellitesChart.destroy();
            topSatellitesChart = new Chart(document.getElementById('top-satellites-chart'), {
                type: 'bar',
                data: {
                    labels: top.map(s => s.name.length > 15 ? s.name.slice(0, 15) + '…' : s.name),
                    datasets: [{
                        label: 'Pass Count',
                        data: top.map(s => s.pass_count),
                        backgroundColor: 'rgba(0, 170, 255, 0.6)',
                        borderColor: '#00aaff',
                        borderWidth: 1
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#a0b4c8' }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: '#a0b4c8' }
                        }
                    }
                }
            });
        })
        .catch(() => {});
}
