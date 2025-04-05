$(document).ready(function() {
    // 初始化变量
    let machines = [];
    let currentImage = null;

    // 加载机台列表
    function loadMachines() {
        $.ajax({
            url: '/api/machines',
            method: 'GET',
            success: function(data) {
                machines = data.map(m => ({
                    ...m,
                    sample_wafers: m.sample_wafers ? m.sample_wafers.split(',') : []
                }));
                renderMachineTable();
            },
            error: function(error) {
                console.error('Error loading machines:', error);
            }
        });
    }

    // 渲染机台表格
    function renderMachineTable(filter = '') {
        const $tableBody = $('#machineTable');
        $tableBody.empty();

        const filteredMachines = machines.filter(machine => 
            machine.machine_id.toLowerCase().includes(filter.toLowerCase()) || 
            machine.name.toLowerCase().includes(filter.toLowerCase())
        );

        filteredMachines.forEach(machine => {
            const $row = $('&lt;tr&gt;');
            $row.append(`&lt;td&gt;${machine.machine_id}&lt;/td&gt;`);
            $row.append(`&lt;td&gt;${machine.name}&lt;/td&gt;`);
            $row.append(`&lt;td&gt;${machine.type}&lt;/td&gt;`);
            $row.append(`&lt;td&gt;${machine.product_id}&lt;/td&gt;`);
            $row.append(`&lt;td&gt;${machine.sample_wafers ? machine.sample_wafers.join(', ') : ''}&lt;/td&gt;`);
            $row.append(`&lt;td&gt;${new Date(machine.created_at).toLocaleString()}&lt;/td&gt;`);
            
            const $actionCell = $('&lt;td&gt;');
            $actionCell.append(`&lt;button class="btn btn-sm btn-primary edit-btn" data-id="${machine.machine_id}"&gt;编辑&lt;/button&gt;`);
            $actionCell.append(' ');
            $actionCell.append(`&lt;button class="btn btn-sm btn-danger delete-btn" data-id="${machine.machine_id}"&gt;删除&lt;/button&gt;`);
            $row.append($actionCell);
            
            $tableBody.append($row);
        });
    }

    // 搜索功能
    $('#searchInput').on('input', function() {
        renderMachineTable($(this).val());
    });

    // 图片上传预览
    $('#imageUpload').on('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                currentImage = e.target.result;
                $('#imagePreview').html(`&lt;img src="${currentImage}" class="preview-img"&gt;`);
            };
            reader.readAsDataURL(file);
        }
    });

    // 保存机台
    $('#saveMachine').on('click', function() {
        const formData = {
            machine_id: $('#machine_id').val(),
            name: $('#name').val(),
            type: $('#type').val(),
            product_id: $('#product_id').val(),
            sample_wafers: $('#sample_wafers').val() ? $('#sample_wafers').val().join(',') : '',
        };

        const method = $('#machineId').val() ? 'PUT' : 'POST';
        const url = $('#machineId').val() ? `/api/machines/${$('#machineId').val()}` : '/api/machines';

        // 如果有图片上传，先处理图片
        if (currentImage && $('#imageUpload')[0].files[0]) {
            const formData = new FormData();
            formData.append('file', $('#imageUpload')[0].files[0]);
            
            $.ajax({
                url: `/api/machines/${$('#machineId').val() || 'new'}/upload`,
                method: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    formData.image_path = response.image_path;
                    saveMachineData(formData, method, url);
                },
                error: function(error) {
                    console.error('Error uploading image:', error);
                }
            });
        } else {
            saveMachineData(formData, method, url);
        }
    });

    function saveMachineData(formData, method, url) {
        $.ajax({
            url: url,
            method: method,
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function() {
                $('#machineModal').modal('hide');
                loadMachines();
                resetForm();
            },
            error: function(error) {
                console.error('Error saving machine:', error);
            }
        });
    }
});

    // 编辑机台
    $(document).on('click', '.edit-btn', function() {
        const machineId = $(this).data('id');
        const machine = machines.find(m => m.id == machineId);
        
        if (machine) {
            $('#machineId').val(machine.id);
            $('#machine_id').val(machine.machine_id);
            $('#name').val(machine.name);
            $('#type').val(machine.type);
            $('#product_id').val(machine.product_id);
            $('#sample_wafers').val(machine.sample_wafers || []);
            
            if (machine.image) {
                currentImage = machine.image;
                $('#imagePreview').html(`&lt;img src="${machine.image}" class="preview-img"&gt;`);
            } else {
                currentImage = null;
                $('#imagePreview').empty();
            }
            
            $('#machineModal').modal('show');
        }
    });

    // 删除机台
    $(document).on('click', '.delete-btn', function() {
        if (confirm('确定要删除这个机台吗？')) {
            const machineId = $(this).data('id');
            $.ajax({
                url: `/api/machines/${machineId}`,
                method: 'DELETE',
                success: function() {
                    loadMachines();
                },
                error: function(error) {
                    console.error('Error deleting machine:', error);
                }
            });
        }
    });

    // 重置表单
    function resetForm() {
        $('#machineForm')[0].reset();
        $('#machineId').val('');
        $('#imagePreview').empty();
        currentImage = null;
    }

    // 初始化模态框关闭时重置表单
    $('#machineModal').on('hidden.bs.modal', function() {
        resetForm();
    });

    // 页面加载时获取机台列表
    $(document).ready(function() {
        loadMachines();
    });
