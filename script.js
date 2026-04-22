/**
 * script.js
 * Handles UI interactions and simulates API calls to AWS DynamoDB endpoints
 * Updated schema to match user's custom DynamoDB item definitions.
 */

// App State
let requestsData = [];

// DOM Elements
const requestGrid = document.getElementById('requestGrid');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');

// Modal Elements
const requestModal = document.getElementById('requestModal');
const openCreateModalBtn = document.getElementById('openCreateModalBtn');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelBtn = document.getElementById('cancelBtn');
const requestForm = document.getElementById('requestForm');
const modalTitle = document.getElementById('modalTitle');

// Form Inputs (Mapped to DynamoDB Schema)
const req_requestId = document.getElementById('req_request_id');
const req_incidentType = document.getElementById('req_incident_type');
const req_status = document.getElementById('req_status');
const req_priorityScore = document.getElementById('req_priority_score');
const req_latitude = document.getElementById('req_latitude');
const req_longitude = document.getElementById('req_longitude');
const req_description = document.getElementById('req_description');
const req_reportedTime = document.getElementById('req_reported_time'); // Hidden input for update carry-over

// Utilities: Generate Mock request_id for DynamoDB simulation
const generateId = () => 'req-' + Math.random().toString(36).substring(2, 9);

// ==== AWS DYNAMODB API CALLS ====
async function fetchRequestsFromDynamoDB() {
    // ====== HOW TO CONNECT TO AWS ======
    // 1. นำ URL API ของคุณ (จาก AWS API Gateway) มาใส่ที่ตัวแปร API_URL_GET ด้านล่าง
    // 2. ลบส่วน "Simulate" ออก และเอาคอมเมนต์ (//) หน้าคำสั่ง fetch ออกเพื่อใช้งานจริง

    const API_URL_GET = "https://ax1zm76s01.execute-api.us-east-1.amazonaws.com/v1/AllRequest";

    try {
        const response = await fetch(API_URL_GET);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        // --- ส่วนตรวจสอบและแกะกล่องข้อมูลจาก API Gateway / Lambda ---
        console.log("Response from API:", data); // เอาไว้ดูโครงสร้างข้อมูลใน Console

        let parsedData = [];
        if (Array.isArray(data)) {
            parsedData = data; // ถ้าเป็น Array อยู่แล้ว
        } else if (data.data && Array.isArray(data.data)) {
            parsedData = data.data; // <=== ดึงข้อมูลจาก "data" (ตรงกับที่ API ของคุณตอบกลับมา)
        } else if (data.Items && Array.isArray(data.Items)) {
            parsedData = data.Items; // ถ้ามาในรูปแบบ DynamoDB "Items" array
        } else if (data.body) {
            parsedData = typeof data.body === 'string' ? JSON.parse(data.body) : data.body;
        }

        return Array.isArray(parsedData) ? parsedData : [];

    } catch (error) {
        console.error("Error fetching from DynamoDB:", error);
        return [];
    }
}

async function saveRequestToDynamoDB(requestObj, isUpdate = false) {
    const API_URL = "https://ax1zm76s01.execute-api.us-east-1.amazonaws.com/v1/report";
    const API_URL_EDIT = "https://ax1zm76s01.execute-api.us-east-1.amazonaws.com/v1/AllRequest";

    let targetUrl = API_URL;
    let methodToUse = 'POST';
    let bodyToSend = {};

    if (isUpdate) {
        // อัปเดตข้อมูล (PATCH) ส่งไปที่ /report/{id}
        targetUrl = `${API_URL_EDIT}/${requestObj.request_id}`;
        methodToUse = 'PATCH';
        bodyToSend = {
            status: requestObj.status,
            priority_score: requestObj.priority_score,
            description: requestObj.description
        };
    } else {
        // สร้างข้อมูลใหม่ (POST) ส่งไปที่ /report
        methodToUse = 'POST';
        bodyToSend = {
            incident_type: requestObj.incident_type,
            latitude: requestObj.latitude,
            longitude: requestObj.longitude,
            description: requestObj.description
        };
    }

    try {
        const response = await fetch(targetUrl, {
            method: methodToUse,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bodyToSend)
        });
        if (!response.ok) throw new Error('Failed to save data');
        return await response.json();
    } catch (error) {
        console.error("Error saving data:", error); throw error;
    }
}

async function deleteRequestFromDynamoDB(id) {
    const API_URL = `https://ax1zm76s01.execute-api.us-east-1.amazonaws.com/v1/AllRequest/${id}`;

    try {
        const response = await fetch(API_URL, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete data');
    } catch (err) {
        console.error("Error deleting:", err);
        throw err; // โยน Error กลับไปให้ UI แจ้งเตือน
    }

    console.log(`Deleting ID ${id} from DynamoDB...`);
    return true;
}


// ==== APP LOGIC ====

async function initApp() {
    requestGrid.innerHTML = `<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><h3>Loading from DynamoDB...</h3></div>`;
    requestsData = await fetchRequestsFromDynamoDB();
    renderRequests();
}

function getStatusBadge(status) {
    const s = (status || "").toLowerCase();
    if (s.includes('resolve') || s === 'done') {
        return 'background-color: var(--success-bg); color: var(--success);';
    } else if (s.includes('progress')) {
        return 'background-color: var(--warning-bg); color: var(--warning);';
    } else {
        return 'background-color: var(--danger-bg); color: var(--danger);'; // New หรือ Pending
    }
}

function renderRequests() {
    const searchTerm = searchInput.value.toLowerCase();
    const sortMode = sortSelect.value;

    // 1. Filter by Search (request_id, trace_id, incident_type)
    let filteredData = requestsData.filter(req =>
        (req.request_id || '').toLowerCase().includes(searchTerm) ||
        (req.trace_id || '').toLowerCase().includes(searchTerm) ||
        (req.incident_type || '').toLowerCase().includes(searchTerm)
    );

    // 2. Sort Data
    filteredData.sort((a, b) => {
        if (sortMode === 'newest') {
            return new Date(b.reported_time) - new Date(a.reported_time);
        } else if (sortMode === 'priority-high') {
            return Number(b.priority_score) - Number(a.priority_score);
        } else if (sortMode === 'priority-low') {
            return Number(a.priority_score) - Number(b.priority_score);
        }
    });

    // 3. Render HTML
    requestGrid.innerHTML = '';

    if (filteredData.length === 0) {
        requestGrid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-folder-open"></i>
                <h3>ไม่มีข้อมูลรายการนี้</h3>
            </div>
        `;
        return;
    }

    filteredData.forEach(req => {
        const priorityColor = req.priority_score >= 8 ? 'var(--danger)' : (req.priority_score >= 5 ? 'var(--warning)' : 'var(--info)');
        const statusStyle = getStatusBadge(req.status);

        const card = document.createElement('div');
        card.className = 'request-card';
        card.innerHTML = `
            <div class="card-header">
                <span class="card-id">#${req.request_id}</span>
                <span class="badge" style="background-color:${priorityColor}20; color:${priorityColor}; border: 1px solid ${priorityColor}40;">
                    Score: ${req.priority_score}
                </span>
            </div>
            <h4 class="card-title" style="display:flex; justify-content:space-between; align-items:flex-start;">
                ${req.incident_type}
                <span style="font-size: 0.75rem; font-weight: 600; padding: 4px 8px; border-radius: 999px; ${statusStyle}">${req.status}</span>
            </h4>
            <p class="card-desc" style="margin-bottom: 12px;">${req.description}</p>
            <div class="card-footer" style="flex-direction: column; align-items: flex-start; gap: 12px; padding-top: 12px;">
                <div class="requester-info" style="font-size: 0.8rem;">
                    <i class="fa-solid fa-location-dot"></i> Lat: ${req.latitude}, Lng: ${req.longitude}
                </div>
                <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
                    <div style="font-size: 0.8rem; color: var(--text-muted);">
                        <i class="fa-solid fa-fingerprint"></i> Trace: ${req.trace_id}
                        <br>
                        <i class="fa-regular fa-clock"></i> ${new Date(req.reported_time).toLocaleDateString()}
                    </div>
                    <div class="card-actions">
                        <button class="icon-btn edit-btn" onclick="openEditModal('${req.request_id}')" title="Edit Request">
                            <i class="fa-solid fa-pen"></i>
                        </button>
                        <button class="icon-btn delete-btn" onclick="handleDelete('${req.request_id}')" title="Delete Request">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        requestGrid.appendChild(card);
    });
}

// ==== EVENT HANDLERS ====

searchInput.addEventListener('input', renderRequests);
sortSelect.addEventListener('change', renderRequests);

function openModal(isEdit = false) {
    const editOnlyFields = document.getElementById('edit_only_fields');
    if (!isEdit) {
        modalTitle.textContent = 'Create New Record';
        requestForm.reset();
        req_requestId.value = '';
        req_reportedTime.value = '';

        // ซ่อนฟิลด์ Status/Score และเปิดให้กรอก Type/Lat/Lng
        if (editOnlyFields) editOnlyFields.style.display = 'none';
        req_incidentType.readOnly = false;
        req_latitude.readOnly = false;
        req_longitude.readOnly = false;
    } else {
        modalTitle.textContent = 'Edit Record';

        // โชว์ฟิลด์ Status/Score และล็อค Type/Lat/Lng ไม่ให้แก้
        if (editOnlyFields) editOnlyFields.style.display = 'flex';
        req_incidentType.readOnly = true;
        req_latitude.readOnly = true;
        req_longitude.readOnly = true;
    }
    requestModal.classList.add('active');
}

function closeModal() { requestModal.classList.remove('active'); }

// ---- แผนที่และพิกัด (Geolocation) ----
const getLocationBtn = document.getElementById('getLocationBtn');
if (getLocationBtn) {
    getLocationBtn.addEventListener('click', () => {
        if (navigator.geolocation) {
            getLocationBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> กำลังหาพิกัด...';
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    req_latitude.value = position.coords.latitude.toFixed(6);
                    req_longitude.value = position.coords.longitude.toFixed(6);
                    getLocationBtn.innerHTML = '<i class="fa-solid fa-check"></i> สำเร็จ!';
                    setTimeout(() => {
                        getLocationBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> ดึงพิกัดปัจจุบัน';
                    }, 2000);
                },
                (error) => {
                    console.error("Geolocation error:", error);
                    alert("ไม่สามารถดึงตำแหน่งได้ กรุณากดอนุญาต (Allow Location) ในเบราว์เซอร์");
                    getLocationBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> ดึงพิกัดปัจจุบัน';
                },
                { enableHighAccuracy: true }
            );
        } else {
            alert("เบราว์เซอร์ของคุณไม่รองรับการดึงตำแหน่งครับ");
        }
    });
}
// -------------------------------------

openCreateModalBtn.addEventListener('click', () => openModal(false));
closeModalBtn.addEventListener('click', closeModal);
cancelBtn.addEventListener('click', closeModal);

requestModal.addEventListener('click', (e) => {
    if (e.target === requestModal) closeModal();
});

// Capture Form Data map to exact Schema
requestForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const nowISO = new Date().toISOString();
    const id = req_requestId.value || generateId();

    // สร้าง Request Object นำไปใช้ส่ง API
    const newRequest = {
        request_id: id,
        incident_type: req_incidentType.value,
        latitude: parseFloat(req_latitude.value),
        longitude: parseFloat(req_longitude.value),
        description: req_description.value,
        status: req_status.value || "New",
        priority_score: Number(req_priorityScore.value) || 5,
        reported_time: req_reportedTime.value || nowISO,
        last_updated: nowISO
    };

    const saveBtn = document.getElementById('saveBtn');
    const originalText = saveBtn.innerText;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
    saveBtn.disabled = true;
    let isUpdate = !!req_requestId.value;
    try {
        await saveRequestToDynamoDB(newRequest, isUpdate);

        // --- สิ่งนี้สำคัญมาก: หลังจากเซฟเสร็จ สั่งดึงข้อมูลล่าสุดจาก API ใหม่อีกครั้งเพื่อเอา ID จริง ---
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading Data...';
        requestsData = await fetchRequestsFromDynamoDB();

    } catch (err) {
        alert("บันทึกข้อมูลไม่สำเร็จ: " + err.message);
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
        return;
    }

    saveBtn.innerHTML = originalText;
    saveBtn.disabled = false;
    closeModal();
    renderRequests();
});

// Inline calls
window.openEditModal = (id) => {
    const req = requestsData.find(r => r.request_id === id);
    if (req) {
        req_requestId.value = req.request_id;
        if (req_incidentType) req_incidentType.value = req.incident_type || "";
        if (req_status) req_status.value = req.status || "New";
        if (req_priorityScore) req_priorityScore.value = req.priority_score || 5;
        req_latitude.value = req.latitude || "";
        req_longitude.value = req.longitude || "";
        req_description.value = req.description || "";
        if (req_reportedTime) req_reportedTime.value = req.reported_time;

        openModal(true);
    }
};

window.handleDelete = async (id) => {
    if (confirm(`คุณแน่ใจหรือไม่ว่าต้องการลบ request_id: ${id} ?`)) {
        const prevData = [...requestsData];
        requestsData = requestsData.filter(r => r.request_id !== id);
        renderRequests();

        try {
            await deleteRequestFromDynamoDB(id);
        } catch (error) {
            console.error("Failed to delete", error);
            requestsData = prevData;
            renderRequests();
            alert("ลบข้อมูลไม่สำเร็จ กรุณาลองใหม่");
        }
    }
};

// Mount App
document.addEventListener('DOMContentLoaded', initApp);
