function showSuccessNotification(message) {
    toastr.success(message);
}

function showErrorNotification(message) {
    toastr.error(message);
}

function openModal(modalId) {
    $(`#${modalId}`).modal('show');
}

function closeModal(modalId) {
    $(`#${modalId}`).modal('hide');
}

function deleteUser(userId) {
    Swal.fire({
        title: 'Tem certeza?',
        text: 'Você não poderá desfazer esta ação!',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sim, excluir!',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/delete_user/${userId}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showSuccessNotification(data.message || 'Usuário excluído com sucesso!');
                        const userRow = document.querySelector(`tr[data-id="${userId}"]`);
                        if (userRow) {
                            userRow.remove();
                        }
                    } else {
                        showErrorNotification(data.error || 'Erro ao excluir o usuário.');
                    }
                })
                .catch(error => {
                    console.error('Erro ao excluir usuário:', error);
                    showErrorNotification('Erro ao excluir usuário.');
                });
        }
    });
}

function submitFormWithFetch(formId, url) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const data = {};
    formData.forEach((value, key) => {
        // Corrigir o checkbox
        if (key === "is_admin") {
            data[key] = true;
        } else {
            data[key] = value;
        }
    });
    if (!formData.has("is_admin")) {
        data["is_admin"] = false;
    }

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessNotification(data.message || 'Usuário criado!');
            form.reset();
        } else {
            showErrorNotification(data.error || 'Erro ao criar usuário.');
        }
    })
    .catch(() => {
        showErrorNotification('Erro ao criar usuário.');
    });
}

function updateTable(tableId, data, rowTemplateCallback) {
    const tableBody = document.getElementById(tableId);
    tableBody.innerHTML = ''; // Limpar a tabela

    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = rowTemplateCallback(item);
        tableBody.appendChild(row);
    });
}

function addPermission(data) {
    fetch('/permissions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessNotification(data.message || 'Permissão adicionada!');
        } else {
            showErrorNotification(data.error || 'Erro ao adicionar permissão.');
        }
    })
    .catch(error => {
        showErrorNotification('Erro ao adicionar permissão.');
    });
}

function startEtl(etlId) {
    fetch(`/etl/start_etl/${etlId}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessNotification(data.message || 'ETL iniciado com sucesso!');
        } else {
            showErrorNotification(data.error || 'Erro ao iniciar o ETL.');
        }
    })
    .catch(error => {
        showErrorNotification('Erro ao iniciar o ETL.');
    });
}

function stopEtl(etlId) {
    fetch(`/etl/stop_etl/${etlId}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessNotification(data.message || 'ETL parado com sucesso!');
        } else {
            showErrorNotification(data.error || 'Erro ao parar o ETL.');
        }
    })
    .catch(error => {
        showErrorNotification('Erro ao parar o ETL.');
    });
}

function stopAllEtls() {
    fetch('/etl/stop_etl', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessNotification(data.message || 'Todos os ETLs foram parados!');
        } else {
            showErrorNotification(data.error || 'Erro ao parar todos os ETLs.');
        }
    })
    .catch(error => {
        showErrorNotification('Erro ao parar todos os ETLs.');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const userForm = document.getElementById('user-form');
    if (userForm) {
        userForm.addEventListener('submit', function(event) {
            event.preventDefault();
            submitFormWithFetch('user-form', userForm.action);
        });
    }
});