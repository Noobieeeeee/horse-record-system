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

