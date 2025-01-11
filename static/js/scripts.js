function showDetails(id) {
    alert("Show details for record: " + id);
}

function editRecord(id) {
    const modal = document.getElementById("edit-modal");
    modal.classList.remove("hidden");
    document.getElementById("edit-id").value = id;

    // Fetch record details via AJAX if needed (optional implementation)
}

function closeModal() {
    const modal = document.getElementById("edit-modal");
    modal.classList.add("hidden");
}

function deleteRecord(id) {
    if (confirm("Are you sure you want to delete this record?")) {
        window.location.href = `/delete/${id}`;
    }
}

function showDeleteModal(id) {
    const modal = document.getElementById("delete-modal");
    modal.classList.remove("hidden");
    modal.dataset.recordId = id; // Store the record ID in the modal
}

function closeModal() {
    const modal = document.getElementById("delete-modal");
    modal.classList.add("hidden");
}

function confirmDelete() {
    const modal = document.getElementById("delete-modal");
    const recordId = modal.dataset.recordId;
    window.location.href = `/delete/${recordId}`;
}

