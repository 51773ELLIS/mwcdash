// Chart.js helper functions for Earnings Dashboard
// Charts are initialized in dashboard.html template

// Global chart instances (will be set by dashboard.html)
let revenueChartInstance = null;
let hoursChartInstance = null;

/**
 * Initialize revenue chart
 * @param {Object} data - Chart data with labels and revenue array
 * @param {string} canvasId - Canvas element ID
 */
function initRevenueChart(data, canvasId = 'revenueChart') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element with id '${canvasId}' not found`);
        return null;
    }
    
    if (revenueChartInstance) {
        revenueChartInstance.destroy();
    }
    
    revenueChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Revenue ($)',
                data: data.revenue,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });
    
    return revenueChartInstance;
}

/**
 * Initialize hours chart
 * @param {Object} data - Chart data with labels and hours array
 * @param {string} canvasId - Canvas element ID
 */
function initHoursChart(data, canvasId = 'hoursChart') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element with id '${canvasId}' not found`);
        return null;
    }
    
    if (hoursChartInstance) {
        hoursChartInstance.destroy();
    }
    
    hoursChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Hours',
                data: data.hours,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgb(54, 162, 235)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(1) + 'h';
                        }
                    }
                }
            }
        }
    });
    
    return hoursChartInstance;
}

/**
 * Update both charts with new data
 * @param {string} period - 'daily', 'weekly', or 'monthly'
 * @param {string} baseUrl - Base API URL (default: '/api/chart_data')
 */
function updateCharts(period, baseUrl = '/api/chart_data') {
    fetch(`${baseUrl}?period=${period}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            initRevenueChart(data);
            initHoursChart(data);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
        });
}

// Export functions for use in templates
if (typeof window !== 'undefined') {
    window.initRevenueChart = initRevenueChart;
    window.initHoursChart = initHoursChart;
    window.updateCharts = updateCharts;
}

