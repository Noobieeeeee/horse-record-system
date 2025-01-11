let currentPage = 1;
const ridersPerPage = 10;

async function fetchLeaderboardData() {
    try {
        const response = await fetch(`/api/leaderboard?page=${currentPage}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching leaderboard data:', error);
        return { riders: [], total_records: 0 };
    }
}

async function renderLeaderboard() {
    const tableBody = document.getElementById('leaderboard').getElementsByTagName('tbody')[0];
    tableBody.innerHTML = "";
    
    const data = await fetchLeaderboardData();
    const riders = data.riders;
    
    riders.forEach((rider, index) => {
        const row = tableBody.insertRow();
        
        const rankCell = row.insertCell(0);
        const riderCell = row.insertCell(1);
        const organizationCell = row.insertCell(2);
        
        const absoluteIndex = (currentPage - 1) * ridersPerPage + index;
        rankCell.innerText = absoluteIndex + 1;
        
        // Create rider info with image and name
        const riderInfo = rider.img 
            ? `<img src="${rider.img}" alt="${rider.name}" class="rider-image"> ${rider.name} (#${rider.horse_number})`
            : `${rider.name} (#${rider.horse_number})`;
        riderCell.innerHTML = riderInfo;

        // this needs to be changed
        // new logic for time and stuff needs to be added.
        
        organizationCell.innerText = rider.organization || '-';
        
        // Apply ranking styles
        if (absoluteIndex === 0) {
            row.classList.add('rank-1');
        } else if (absoluteIndex === 1) {
            row.classList.add('rank-2');
        } else if (absoluteIndex === 2) {
            row.classList.add('rank-3');
        }
    });
    
    // Update pagination buttons
    const totalPages = Math.ceil(data.total_records / ridersPerPage);
    document.getElementById('prev').disabled = currentPage === 1;
    document.getElementById('next').disabled = currentPage >= totalPages;
}

async function changePage(direction) {
    currentPage += direction;
    await renderLeaderboard();
}

// Initial render
renderLeaderboard();