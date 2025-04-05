document.addEventListener('DOMContentLoaded', function() {
    // 获取数据并更新看板
    fetchDashboardData();

    // 设置定时刷新（每5秒刷新一次）
    setInterval(fetchDashboardData, 5000);
});

function fetchDashboardData() {
    fetch('/api/dashboard')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应不正常');
            }
            return response.json();
        })
        .then(data => {
            // 更新页面上的数字
            document.getElementById('files-generated').textContent = data.files_generated || 0;
            document.getElementById('errors-count').textContent = data.error_files || 0;  // 修改这里
            document.getElementById('success-files').textContent = data.success_files || 0;
            document.getElementById('success-rate').textContent = (data.success_rate || 0) + '%';
            document.getElementById('failure-files').textContent = data.failure_files || 0;

            // 更新图表数据
            updateChart(data);
        })
        .catch(error => {
            console.error('获取数据失败:', error);
            // 显示错误信息
            const cards = document.querySelectorAll('.stat-value');
            cards.forEach(card => {
                card.textContent = '--';
            });
        });
}

// 图表更新函数
function updateChart(data) {
    const ctx = document.getElementById('dashboardChart').getContext('2d');

    // 更新图表
    if (window.dashboardChart) {
        window.dashboardChart.destroy(); // 销毁旧的图表
    }

    // 创建新的图表
    window.dashboardChart = new Chart(ctx, {
        type: 'pie',  // 图表类型
        data: {
            labels: ['成功文件', '失败文件', '错误文件'],
            datasets: [{
                label: '文件统计',
                data: [
                    data.success_files || 0,
                    data.failure_files || 0,
                    data.error_files || 0
                ],
                backgroundColor: ['#4caf50', '#f44336', '#ff9800'],
                borderColor: '#fff',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            return tooltipItem.label + ': ' + tooltipItem.raw;
                        }
                    }
                }
            }
        }
    });
}
