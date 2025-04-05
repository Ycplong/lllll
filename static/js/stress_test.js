$(document).ready(function() {
    // 加载机台列表
    loadMachineList();
    
    // 启动压测按钮点击事件
    $('#startTest').click(function() {
        startStressTest();
    });
    
    // 停止压测按钮点击事件
    $('#stopTest').click(function() {
        stopStressTest();
    });
});

// 加载机台列表
function loadMachineList() {
    $.ajax({
        url: '/api/machines',
        method: 'GET',
        success: function(data) {
            let machineList = $('#machineList');
            machineList.empty();
            
            data.forEach(function(machine) {
                machineList.append(`
                    &lt;a href="#" class="list-group-item list-group-item-action machine-item" 
                       data-machine-id="${machine.id}"&gt;
                        ${machine.name}
                    &lt;/a&gt;
                `);
            });
            
            // 机台选择事件
            $('.machine-item').click(function() {
                selectMachine($(this).data('machine-id'));
            });
        },
        error: function(error) {
            console.error('Error loading machines:', error);
        }
    });
}

// 选择机台
function selectMachine(machineId) {
    $.ajax({
        url: `/api/machines/${machineId}/wafers`,
        method: 'GET',
        success: function(data) {
            let wafersContainer = $('#selectedWafers');
            wafersContainer.empty();
            
            if (data.length > 0) {
                data.forEach(function(wafer) {
                    wafersContainer.append(`&lt;div&gt;${wafer.name}&lt;/div&gt;`);
                });
            } else {
                wafersContainer.append('&lt;div class="text-muted"&gt;该机台没有Sample Wafers&lt;/div&gt;');
            }
        },
        error: function(error) {
            console.error('Error loading wafers:', error);
        }
    });
}

// 启动压测
function startStressTest() {
    let formData = {
        startDate: $('#startDate').val(),
        endDate: $('#endDate').val(),
        machineId: $('#machineSelect').val(),
        batchCount: $('#batchCount').val()
    };
    
    if (!formData.machineId) {
        showAlert('请先选择机台', 'warning');
        return;
    }
    
    if (!formData.startDate || !formData.endDate) {
        showAlert('请设置开始和结束时间', 'warning');
        return;
    }
    
    $('#startTest').prop('disabled', true);
    $('#stopTest').prop('disabled', false);
    
    $.ajax({
        url: '/api/tasks',
        method: 'POST',
        data: JSON.stringify({
            machine_ids: [formData.machineId],
            start_time: formData.startDate,
            end_time: formData.endDate
        }),
        contentType: 'application/json',
        success: function(data) {
            updateTaskStatus('压测已启动');
            monitorProgress(data.task_id);
        },
        error: function(error) {
            console.error('Error starting stress test:', error);
            $('#startTest').prop('disabled', false);
            updateTaskStatus('压测启动失败: ' + error.responseJSON.message);
        }
    });
}

// 停止压测
function stopStressTest() {
    // 新API不支持直接停止任务，改为更新状态显示
    updateTaskStatus('压测任务将在当前批次完成后停止');
    $('#startTest').prop('disabled', false);
    $('#stopTest').prop('disabled', true);
}

// 监控进度
function monitorProgress(taskId) {
    let progressInterval = setInterval(function() {
        $.ajax({
            url: `/api/tasks/${taskId}`,
            method: 'GET',
            success: function(data) {
                const progress = calculateProgress(data);
                updateProgress(progress, data.status);
                
                // 更新统计信息
                if (data.batches_completed || data.errors_count) {
                    const totalBatches = parseInt($('#batchCount').val());
                    const batchProgress = Math.round((data.batches_completed / totalBatches) * 100);
                    const successRate = data.batches_completed > 0 ? 
                        Math.round(((data.batches_completed - data.errors_count) / data.batches_completed) * 100) : 0;
                    
                    $('#statsInfo').html(`
                        <div>已完成批次: ${data.batches_completed}/${totalBatches}</div>
                        <div>错误批次: ${data.errors_count}</div>
                        <div>批次进度: ${batchProgress}%</div>
                        <div>批次成功率: ${successRate}%</div>
                    `);
                }
                
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(progressInterval);
                    $('#startTest').prop('disabled', false);
                    $('#stopTest').prop('disabled', true);
                    
                    // 最终状态更新
                    if (data.status === 'completed') {
                        updateTaskStatus('压测完成');
                    } else {
                        updateTaskStatus('压测失败');
                    }
                }
            },
            error: function(error) {
                console.error('Error getting progress:', error);
                clearInterval(progressInterval);
                updateTaskStatus('获取进度失败');
            }
        });
    }, 2000); // 调整为2秒轮询一次，减轻服务器压力
}

// 更新进度条
function calculateProgress(taskData) {
    if (!taskData.start_time || !taskData.end_time) return 0;
    const start = new Date(taskData.start_time);
    const end = new Date(taskData.end_time);
    const now = new Date();
    return Math.min(100, Math.max(0, 
        ((now - start) / (end - start)) * 100
    ));
}

function updateProgress(progress, status) {
    let progressBar = $('#progressBar');
    const displayProgress = Math.round(progress);
    progressBar.css('width', displayProgress + '%');
    progressBar.text(displayProgress + '%');
    
    if (status === 'failed') {
        progressBar.addClass('bg-danger');
    } else if (progress >= 100) {
        progressBar.addClass('bg-success');
    } else {
        progressBar.removeClass('bg-danger bg-success');
    }
    
    updateTaskStatus(status);
}

// 更新任务状态
function updateTaskStatus(status) {
    $('#taskStatus').text(status);
}

// 显示提示信息
function showAlert(message, type) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // 移除旧的提示
    $('.alert').alert('close');
    
    // 添加新提示到容器顶部
    $('.container').prepend(alertHtml);
}