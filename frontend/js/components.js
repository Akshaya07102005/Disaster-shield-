// Shared UI Component Library for Disaster Shield AI

const components = {
    // Renders the top navigation bar with dynamic notifications and user profile
    renderNavbar: (title = "Disaster Shield AI") => {
        const user = api.getUser();
        const userName = user ? user.name : "Guest User";
        const roleLabel = user ? user.role.toUpperCase() : "GUEST";
        
        const html = `
            <div class="navbar-brand" onclick="window.location.href='/'" style="cursor: pointer;">
                <i class="fa-solid fa-shield-halved" style="color: var(--color-critical); margin-right: 8px;"></i>
                <span style="font-weight: 800; letter-spacing: 0.03em;">DISASTER SHIELD AI</span>
                <span class="user-badge role-${user ? user.role : 'guest'}" style="margin-left: 10px; font-size: 10px; text-transform: uppercase;">
                    ${roleLabel} PORTAL
                </span>
            </div>
            <div class="navbar-user">
                <!-- Hamburger menu for mobile views -->
                <button class="mobile-toggle-btn" onclick="components.toggleSidebar()" style="display: none; background: transparent; border: none; color: white; font-size: 20px; cursor: pointer; margin-right: 15px;">
                    <i class="fa-solid fa-bars"></i>
                </button>

                <!-- Notifications Dropdown -->
                <div class="notify-center" onclick="components.toggleNotificationDropdown(event)">
                    <i class="fa-solid fa-bell" style="font-size: 18px; color: white; cursor: pointer;"></i>
                    <span class="notify-badge" id="navbar-notify-count" style="display: none;">0</span>
                    <div class="notify-dropdown" id="navbar-notify-dropdown" style="display: none;">
                        <div class="notify-header">
                            <span>NOTIFICATIONS</span>
                            <a href="#" onclick="components.markAllNotificationsRead(event)" style="font-size: 11px; text-decoration: none; color: var(--color-info);">Mark all read</a>
                        </div>
                        <div id="notify-dropdown-list">
                            <div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 12px;">No active alerts.</div>
                        </div>
                    </div>
                </div>
                
                <span class="user-profile-badge"><i class="fa-solid fa-user-circle"></i> ${userName}</span>
                <button class="btn btn-secondary" onclick="api.logout()" style="padding: 6px 12px; width: auto; font-size: 12px; display: inline-flex; align-items: center; gap: 4px; border-radius: 4px;">
                    <i class="fa-solid fa-right-from-bracket"></i> Logout
                </button>
            </div>
        `;
        
        const header = document.querySelector('header.app-navbar');
        if (header) {
            header.innerHTML = html;
        }
        
        // Start notification polling
        components.pollNotifications();
        if (!window._notifPollInterval) {
            window._notifPollInterval = setInterval(components.pollNotifications, 10000);
        }
        
        // Initialize real-time Socket.IO listener and buzzer if io is loaded
        components.initSocket();
    },

    // Web Audio API Synthesized Emergency Buzzer
    playEmergencyBuzzer: () => {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            
            const playTone = (freq, startTime, duration) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(freq, ctx.currentTime + startTime);
                gain.gain.setValueAtTime(0.18, ctx.currentTime + startTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startTime + duration);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime + startTime);
                osc.stop(ctx.currentTime + startTime + duration);
            };
            
            playTone(880, 0, 0.25);
            playTone(880, 0.35, 0.25);
            playTone(1100, 0.7, 0.4);
        } catch (e) {
            console.log('AudioContext buzzer:', e);
        }
    },

    // Visual Emergency Toast Alert
    showEmergencyToast: (title, message) => {
        let container = document.getElementById('emergency-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'emergency-toast-container';
            container.style.cssText = "position: fixed; top: 20px; right: 20px; z-index: 99999; display: flex; flex-direction: column; gap: 10px; max-width: 420px;";
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = 'glass-panel';
        toast.style.cssText = "background: #C22B2B; color: white; border: 2px solid rgba(255,255,255,0.4); box-shadow: 0 8px 30px rgba(194,43,43,0.5); padding: 14px 18px; border-radius: 10px; display: flex; gap: 12px; align-items: flex-start;";
        toast.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation" style="font-size: 24px; color: white; margin-top: 2px;"></i>
            <div style="flex: 1;">
                <div style="font-weight: 800; font-size: 14px; margin-bottom: 3px;">${title}</div>
                <div style="font-size: 12px; opacity: 0.95; line-height: 1.4;">${message}</div>
            </div>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 15px; opacity: 0.8;"><i class="fa-solid fa-xmark"></i></button>
        `;
        container.appendChild(toast);
        setTimeout(() => { if (toast.parentElement) toast.remove(); }, 9000);
    },

    // Initialize Socket.IO connection and join role room
    initSocket: () => {
        if (window._socketInitialized || typeof io === 'undefined') return;
        try {
            const user = api.getUser();
            const socketUrl = (typeof api !== 'undefined' && api.getSocketUrl) ? api.getSocketUrl() : undefined;
            const socket = io(socketUrl, {
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: Infinity
            });
            window._socketInstance = socket;
            window._socketInitialized = true;

            socket.on('connect', () => {
                console.log('Real-time Socket.IO connected:', socket.id);
                if (user && user.role) {
                    socket.emit('join_room', { room: user.role });
                }
            });

            // Incoming SOS Request Handler (Government & NGO Command Alert)
            const handleSos = (data) => {
                console.log('Incoming SOS event:', data);
                components.pollNotifications();
                if (user && (user.role === 'gov' || user.role === 'ngo')) {
                    components.playEmergencyBuzzer();
                    const areaName = data.area_name || (data.area ? data.area.area_name : 'Chennai Sector');
                    components.showEmergencyToast(
                        `🚨 EMERGENCY SOS #${data.id || 'NEW'} RECEIVED`,
                        `${data.emergency_type || 'Disaster'} reported in ${areaName}. Priority Score: ${(data.priority_score || 0).toFixed(1)}.`
                    );
                }
            };

            socket.on('new_sos_request', handleSos);
            socket.on('new_sos', handleSos);

            // Incoming Alert Handler
            socket.on('new_alert', (alert) => {
                components.pollNotifications();
                components.showEmergencyToast(
                    `⚠️ EMERGENCY WARNING: ${alert.title}`,
                    `[${(alert.severity || 'WARNING').toUpperCase()}] ${alert.description || ''}`
                );
            });

            // Status Changed Handler
            socket.on('sos_status_changed', (data) => {
                components.pollNotifications();
            });

        } catch (e) {
            console.log('Socket init exception:', e);
        }
    },

    // Renders the side bar dynamically based on the user's role
    renderSidebar: (activePath = "") => {
        const user = api.getUser();
        if (!user) {
            window.location.href = '/login.html';
            return;
        }
        
        let links = [];
        if (user.role === 'citizen') {
            links = [
                { label: "Dashboard", icon: "fa-gauge", path: "/citizen/dashboard.html" },
                { label: "Request Help", icon: "fa-circle-exclamation", path: "/citizen/request-help.html" },
                { label: "My Requests", icon: "fa-list", path: "/citizen/requests.html" },
                { label: "Nearby Shelters", icon: "fa-house-shield", path: "/citizen/shelters.html" },
                { label: "Live Tracking", icon: "fa-location-crosshairs", path: "/citizen/tracking.html" },
                { label: "AI Emergency Assistant", icon: "fa-robot", path: "/citizen/assistant.html" }
            ];
        } else if (user.role === 'ngo') {
            links = [
                { label: "Dashboard", icon: "fa-gauge", path: "/ngo/dashboard.html" },
                { label: "Mission Command", icon: "fa-earth-asia", path: "/ngo/index.html" },
                { label: "Emergency Requests", icon: "fa-list-check", path: "/ngo/requests.html" },
                { label: "Critical Cases", icon: "fa-triangle-exclamation", path: "/ngo/critical.html" },
                { label: "Team Management", icon: "fa-users-gear", path: "/ngo/teams.html" },
                { label: "Member Management", icon: "fa-id-card", path: "/ngo/members.html" },
                { label: "Disaster Operations", icon: "fa-cloud-meatball", path: "/ngo/disaster-analysis.html" },
                { label: "Food Operations", icon: "fa-bowl-rice", path: "/ngo/food-analysis.html" },
                { label: "Shelter Operations", icon: "fa-tents", path: "/ngo/shelter-analysis.html" },
                { label: "Resource Allocation", icon: "fa-truck-moving", path: "/ngo/resources.html" },
                { label: "Live Operations Map", icon: "fa-map-location-dot", path: "/ngo/map.html" },
                { label: "AI Support Assistant", icon: "fa-robot", path: "/ngo/assistant.html" }
            ];
        } else if (user.role === 'gov') {
            links = [
                { label: "Dashboard", icon: "fa-chart-pie", path: "/government/dashboard.html" },
                { label: "Disaster Monitoring", icon: "fa-bolt-lightning", path: "/government/monitoring.html" },
                { label: "Emergency Requests", icon: "fa-circle-exclamation", path: "/government/requests.html" },
                { label: "Critical Cases", icon: "fa-triangle-exclamation", path: "/government/critical.html" },
                { label: "NGO Operations", icon: "fa-handshake-angle", path: "/government/ngos.html" },
                { label: "Shelter Monitoring", icon: "fa-house-circle-exclamation", path: "/government/shelters.html" },
                { label: "Food Distribution", icon: "fa-wheat-awn", path: "/government/distribution.html" },
                { label: "Live Command Map", icon: "fa-earth-asia", path: "/government/map.html" },
                { label: "Reports & Exporters", icon: "fa-file-pdf", path: "/government/reports.html" },
                { label: "Command Analytics", icon: "fa-chart-line", path: "/government/analytics.html" },
                { label: "AI Decision Intelligence", icon: "fa-wand-magic-sparkles", path: "/government/intelligence.html" },
                { label: "Global Policy Index (GPI)", icon: "fa-globe", path: "/government/gpi.html" },
                { label: "Resource Inventories", icon: "fa-warehouse", path: "/government/resources.html" },
                { label: "Response Squads", icon: "fa-helmet-safety", path: "/government/teams.html" },
                { label: "Regional Alert Manager", icon: "fa-bullhorn", path: "/government/alerts.html" }
            ];
        }
        
        let html = `<div class="sidebar-wrapper">`;
        links.forEach(l => {
            const activeClass = activePath.endsWith(l.path) ? "active" : "";
            html += `
                <a href="${l.path}" class="sidebar-link ${activeClass}">
                    <i class="fa-solid ${l.icon}"></i> <span>${l.label}</span>
                </a>
            `;
        });
        html += `</div>`;
        
        const sidebar = document.querySelector('aside.sidebar');
        if (sidebar) {
            sidebar.innerHTML = html;
        }
    },

    toggleSidebar: () => {
        const sidebar = document.querySelector('aside.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('expanded');
        }
    },

    // Global notifications poller
    pollNotifications: async () => {
        try {
            const list = await api.request('/api/citizen/notifications');
            const countBadge = document.getElementById('navbar-notify-count');
            const dropdownList = document.getElementById('notify-dropdown-list');
            
            const unread = list.filter(n => !n.read);
            
            if (countBadge) {
                if (unread.length > 0) {
                    countBadge.innerText = unread.length;
                    countBadge.style.display = 'flex';
                } else {
                    countBadge.style.display = 'none';
                }
            }
            
            if (dropdownList) {
                if (list.length === 0) {
                    dropdownList.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 12px;">No active alerts.</div>`;
                } else {
                    dropdownList.innerHTML = '';
                    list.slice(0, 5).forEach(n => {
                        const date = new Date(n.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        const readClass = n.read ? 'read' : 'unread';
                        
                        const item = document.createElement('div');
                        item.className = `notify-item ${readClass}`;
                        item.innerHTML = `
                            <strong>${n.title}</strong>
                            <p>${n.body}</p>
                            <span class="notify-time">${date}</span>
                        `;
                        dropdownList.appendChild(item);
                    });
                }
            }
        } catch (e) {
            console.error("Failed to check notifications:", e);
        }
    },

    toggleNotificationDropdown: (e) => {
        e.stopPropagation();
        const dropdown = document.getElementById('navbar-notify-dropdown');
        if (dropdown) {
            dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
        }
    },

    markAllNotificationsRead: async (e) => {
        e.preventDefault();
        e.stopPropagation();
        try {
            await api.request('/api/citizen/notifications', { method: 'PUT' });
            components.pollNotifications();
        } catch (e) {
            console.error(e);
        }
    },

    // Shared reusable Datatable component
    renderDataTable: (containerId, columns, data, options = {}) => {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        let html = `
            <div class="table-container">
                <table class="datatable">
                    <thead>
                        <tr>
        `;
        
        // Headers
        columns.forEach(col => {
            const sortable = col.sortable ? 'sortable' : '';
            html += `<th class="${sortable}" data-col="${col.field}">${col.title}</th>`;
        });
        
        html += `
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        // Rows
        if (data.length === 0) {
            html += `<tr><td colspan="${columns.length}" style="text-align: center; color: var(--text-muted); padding: 30px;">No matching records found.</td></tr>`;
        } else {
            data.forEach(row => {
                html += `<tr>`;
                columns.forEach(col => {
                    let cellVal = row[col.field];
                    if (col.render) {
                        cellVal = col.render(cellVal, row);
                    }
                    html += `<td>${cellVal !== undefined ? cellVal : ''}</td>`;
                });
                html += `</tr>`;
            });
        }
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        // Add Pagination if specified
        if (options.pagination) {
            const page = options.pagination.page || 1;
            const pages = options.pagination.pages || 1;
            const total = options.pagination.total || 0;
            
            html += `
                <div class="pagination-panel">
                    <span class="pagination-info">Showing ${data.length} of ${total} records</span>
                    <div class="pagination-buttons">
                        <button class="btn btn-secondary" onclick="${options.pagination.onPrevPage}" ${page <= 1 ? 'disabled' : ''}>Prev</button>
                        <span class="pagination-page">Page ${page} of ${pages}</span>
                        <button class="btn btn-secondary" onclick="${options.pagination.onNextPage}" ${page >= pages ? 'disabled' : ''}>Next</button>
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
        
        // Hook sorting events
        if (options.onSort) {
            container.querySelectorAll('th.sortable').forEach(th => {
                th.addEventListener('click', () => {
                    const field = th.getAttribute('data-col');
                    options.onSort(field);
                });
            });
        }
    },

    // Modal Confirmation Dialog Helper
    showConfirmationDialog: (title, message, onConfirm) => {
        let dialog = document.getElementById('confirmation-dialog');
        if (!dialog) {
            dialog = document.createElement('div');
            dialog.id = 'confirmation-dialog';
            dialog.className = 'confirmation-modal-overlay';
            document.body.appendChild(dialog);
        }
        
        dialog.innerHTML = `
            <div class="glass-panel confirmation-modal-card">
                <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--color-critical);"></i> ${title}</h3>
                <p style="margin-top: 10px; margin-bottom: 20px; font-size: 13px; color: var(--text-secondary); line-height: 1.45;">${message}</p>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="btn btn-secondary" id="confirm-cancel" style="width: auto; padding: 8px 16px;">Cancel</button>
                    <button class="btn btn-danger" id="confirm-ok" style="width: auto; padding: 8px 16px;">Confirm</button>
                </div>
            </div>
        `;
        
        dialog.style.display = 'flex';
        
        dialog.querySelector('#confirm-cancel').onclick = () => {
            dialog.style.display = 'none';
        };
        
        dialog.querySelector('#confirm-ok').onclick = () => {
            dialog.style.display = 'none';
            onConfirm();
        };
    },

    // 40 Default Categorized Questions for Disaster Shield Bots
    portalStarterQuestions: {
        citizen: [
            "How do I send an SOS alert?",
            "Where is the nearest shelter to me?",
            "What should I keep in an emergency go-bag?",
            "How do I track my assigned rescue team?",
            "Who do I call if I can't reach the app?"
        ],
        ngo: [
            "How do I form a new rescue squad?",
            "How do I check volunteer availability by skill?",
            "How is SOS priority score calculated?",
            "How do I report a food/shelter deficit?",
            "What equipment is recommended for a flood mission?"
        ],
        gov: [
            "Show me all Critical-risk sectors right now.",
            "How do I verify a new NGO?",
            "How do I generate today's situation report PDF?",
            "What triggers a flash-flood warning?",
            "Show unresolved SOS requests older than 30 minutes."
        ]
    },

    // 40 Default Categorized Questions for Disaster Shield Bots
    botQuestions: [
        { id: 1, category: "Flood & Rain", icon: "fa-water", q: "What should I do during a flood?" },
        { id: 2, category: "Flood & Rain", icon: "fa-water", q: "What is the waterlogging protocol in Chennai?" },
        { id: 3, category: "Flood & Rain", icon: "fa-water", q: "How to purify drinking water during a flood?" },
        { id: 4, category: "Flood & Rain", icon: "fa-water", q: "What to do if floodwater enters my house?" },
        { id: 5, category: "Flood & Rain", icon: "fa-water", q: "How to safely evacuate a flooded area?" },
        { id: 6, category: "Flood & Rain", icon: "fa-water", q: "What should I do if a car gets caught in floodwater?" },
        
        { id: 7, category: "Cyclone & Storm", icon: "fa-wind", q: "How to prepare for a cyclone?" },
        { id: 8, category: "Cyclone & Storm", icon: "fa-wind", q: "What should I do during a severe cyclonic storm?" },
        { id: 9, category: "Cyclone & Storm", icon: "fa-wind", q: "What precautions should be taken after a cyclone passes?" },
        { id: 10, category: "Cyclone & Storm", icon: "fa-wind", q: "What is the average rainfall during Chennai monsoons?" },
        { id: 11, category: "Cyclone & Storm", icon: "fa-wind", q: "How to report a fallen tree or broken electric pole?" },
        
        { id: 12, category: "Helplines", icon: "fa-phone-volume", q: "What are the emergency contact numbers in Chennai?" },
        { id: 13, category: "Helplines", icon: "fa-phone-volume", q: "How to contact the Greater Chennai Corporation?" },
        { id: 14, category: "Helplines", icon: "fa-phone-volume", q: "How to contact the Electricity Board for power hazards?" },
        { id: 15, category: "Helplines", icon: "fa-phone-volume", q: "How to contact Tamil Nadu State Disaster Management Authority (TNSDMA)?" },
        
        { id: 16, category: "Survival Kit", icon: "fa-briefcase-medical", q: "What should be in an emergency survival kit?" },
        { id: 17, category: "Survival Kit", icon: "fa-briefcase-medical", q: "How much drinking water should be stored per person?" },
        { id: 18, category: "Survival Kit", icon: "fa-briefcase-medical", q: "How to safely store food during power outages?" },
        { id: 19, category: "Survival Kit", icon: "fa-briefcase-medical", q: "What documents should be kept in a waterproof bag?" },
        
        { id: 20, category: "First Aid", icon: "fa-heart-pulse", q: "First aid for electric shock?" },
        { id: 21, category: "First Aid", icon: "fa-heart-pulse", q: "How to treat dehydration or heat stroke?" },
        { id: 22, category: "First Aid", icon: "fa-heart-pulse", q: "What to do if someone is drowning or submerged?" },
        { id: 23, category: "First Aid", icon: "fa-heart-pulse", q: "How to handle snake bites or waterborne infections in floods?" },
        { id: 24, category: "First Aid", icon: "fa-heart-pulse", q: "How to handle food poisoning in emergency camps?" },
        
        { id: 25, category: "Shelters", icon: "fa-tents", q: "What are the rules for shelter occupancy?" },
        { id: 26, category: "Shelters", icon: "fa-tents", q: "What is the maximum capacity of relief shelters?" },
        { id: 27, category: "Shelters", icon: "fa-tents", q: "Are pets allowed in emergency shelters?" },
        { id: 28, category: "Shelters", icon: "fa-tents", q: "What medical facilities are available at relief camps?" },
        
        { id: 29, category: "Risk & Zones", icon: "fa-map-location-dot", q: "How is the area risk score calculated?" },
        { id: 30, category: "Risk & Zones", icon: "fa-map-location-dot", q: "What does Risk Level Green, Yellow, Orange, and Red mean?" },
        { id: 31, category: "Risk & Zones", icon: "fa-map-location-dot", q: "What are the 15 zone boundaries of Chennai?" },
        { id: 32, category: "Risk & Zones", icon: "fa-map-location-dot", q: "What is the current risk level in Velachery?" },
        { id: 33, category: "Risk & Zones", icon: "fa-map-location-dot", q: "What is the risk level in Pallikaranai and T. Nagar?" },
        
        { id: 34, category: "SOS & Rescue", icon: "fa-tower-broadcast", q: "How do citizens report emergencies using SOS?" },
        { id: 35, category: "SOS & Rescue", icon: "fa-tower-broadcast", q: "How does the SOS priority scoring algorithm work?" },
        { id: 36, category: "SOS & Rescue", icon: "fa-tower-broadcast", q: "How can family members track an active SOS rescue status?" },
        
        { id: 37, category: "NGOs & Volunteers", icon: "fa-hand-holding-heart", q: "How to sign up as a disaster response volunteer?" },
        { id: 38, category: "NGOs & Volunteers", icon: "fa-hand-holding-heart", q: "How are rescue teams and inflatable boats deployed?" },
        { id: 39, category: "NGOs & Volunteers", icon: "fa-hand-holding-heart", q: "How can an NGO get verified by the government?" },
        { id: 40, category: "NGOs & Volunteers", icon: "fa-hand-holding-heart", q: "How to request additional resources like boats, food, and medical kits?" }
    ],

    // Helper to format text with bold, linebreaks, and list markers
    formatAIResponse: (rawText) => {
        if (!rawText) return "No response received.";
        let formatted = rawText
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\[AI Recommendation — Human Verification Required\]\n\n/g, '<div style="font-size:10px; color:var(--color-medium); font-weight:700; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;"><i class="fa-solid fa-shield-halved"></i> Advisory Verification Mode</div>')
            .replace(/\n\n/g, '<br/><br/>')
            .replace(/\n/g, '<br/>');
        return formatted;
    },

    // Renders the AI Chat Assistant panel with 5 Quick Starter Chips & 40 categorized questions
    renderAIChatPanel: (containerId, endpoint = '/api/citizen/assistant') => {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const user = api.getUser();
        const role = user ? user.role : 'citizen';
        const starterList = components.portalStarterQuestions[role] || components.portalStarterQuestions.citizen;

        let starterChipsHtml = '';
        starterList.forEach(q => {
            starterChipsHtml += `<button class="ai-question-chip starter-chip" style="font-weight:600; font-size:11px; background:rgba(44,74,124,0.06); border:1px solid rgba(44,74,124,0.2);"><i class="fa-solid fa-bolt" style="color:var(--color-warning);"></i> ${q}</button>`;
        });
        
        container.className = "glass-panel ai-chat-box";
        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <h3 style="margin: 0; font-size: 16px;"><i class="fa-solid fa-robot" style="color: var(--color-success);"></i> AI Decision Assistant</h3>
                <span class="badge badge-success" style="font-size: 10px;"><i class="fa-solid fa-bolt"></i> Ready</span>
            </div>
            <div class="ai-warning-label"><i class="fa-solid fa-circle-info"></i> AI Decision Support Mode — Human Verification Required. No life-critical decisions should be made autonomously.</div>
            
            <!-- Quick Portal Starter Chips -->
            <div style="margin-top: 6px; margin-bottom: 8px;">
                <div style="font-size: 11px; font-weight: 700; color: var(--color-primary-light); margin-bottom: 4px;">
                    <i class="fa-solid fa-star" style="color: var(--color-warning);"></i> Quick Questions for ${role.toUpperCase()}:
                </div>
                <div id="ai-quick-starter-chips" style="display: flex; gap: 6px; flex-wrap: wrap;">
                    ${starterChipsHtml}
                </div>
            </div>

            <!-- Chat history -->
            <div class="chat-history" id="ai-chat-history" style="flex: 1; min-height: 180px; max-height: 280px; overflow-y: auto; padding: 8px 4px;">
                <div class="chat-bubble ai">
                    <strong>Hello!</strong> I am your AI Decision Assistant. Click any quick question above, choose from the <strong>40 categorized questions</strong> below, or type your query:
                </div>
            </div>

            <!-- 40 Suggested Questions Explorer -->
            <div class="ai-suggested-wrapper">
                <div class="ai-browse-header">
                    <span><i class="fa-solid fa-lightbulb" style="color: var(--color-warning);"></i> Standard Disaster Knowledge Base (40)</span>
                    <button class="ai-toggle-btn" id="btn-toggle-chips"><i class="fa-solid fa-chevron-up"></i> Hide</button>
                </div>
                
                <div id="ai-chips-container" style="display: flex; flex-direction: column; gap: 6px;">
                    <!-- Category Tabs -->
                    <div class="ai-category-tabs" id="ai-category-tabs">
                        <button class="ai-category-tab active" data-cat="All">All (40)</button>
                        <button class="ai-category-tab" data-cat="Flood & Rain"><i class="fa-solid fa-water"></i> Flood & Rain (6)</button>
                        <button class="ai-category-tab" data-cat="Cyclone & Storm"><i class="fa-solid fa-wind"></i> Cyclone & Storm (5)</button>
                        <button class="ai-category-tab" data-cat="Helplines"><i class="fa-solid fa-phone-volume"></i> Helplines (4)</button>
                        <button class="ai-category-tab" data-cat="Survival Kit"><i class="fa-solid fa-briefcase-medical"></i> Kit & Supplies (4)</button>
                        <button class="ai-category-tab" data-cat="First Aid"><i class="fa-solid fa-heart-pulse"></i> First Aid (5)</button>
                        <button class="ai-category-tab" data-cat="Shelters"><i class="fa-solid fa-tents"></i> Shelters (4)</button>
                        <button class="ai-category-tab" data-cat="Risk & Zones"><i class="fa-solid fa-map-location-dot"></i> Risk & Zones (5)</button>
                        <button class="ai-category-tab" data-cat="SOS & Rescue"><i class="fa-solid fa-tower-broadcast"></i> SOS & Rescue (3)</button>
                        <button class="ai-category-tab" data-cat="NGOs & Volunteers"><i class="fa-solid fa-hand-holding-heart"></i> NGOs & Volunteers (4)</button>
                    </div>

                    <!-- Search Filter inside chips -->
                    <div style="position: relative;">
                        <input type="text" id="ai-q-search" class="form-control" placeholder="Search across 40 disaster questions..." style="padding: 4px 8px 4px 26px; font-size: 11px; height: 26px;">
                        <i class="fa-solid fa-magnifying-glass" style="position: absolute; left: 8px; top: 7px; font-size: 11px; color: var(--text-muted);"></i>
                    </div>

                    <!-- Question Chips list -->
                    <div class="ai-question-chips" id="ai-question-chips"></div>
                </div>
            </div>

            <!-- Input area -->
            <div style="display: flex; gap: 6px; margin-top: auto; padding-top: 4px;">
                <input class="form-control" type="text" id="ai-chat-input" placeholder="Type a disaster question or click a suggested question above..." style="padding: 8px 12px; font-size: 12px;">
                <button class="btn btn-primary" id="btn-send-ai" style="width: auto; padding: 8px 16px;">
                    <i class="fa-solid fa-paper-plane"></i>
                </button>
            </div>
        `;
        
        const input = container.querySelector('#ai-chat-input');
        const history = container.querySelector('#ai-chat-history');
        const sendBtn = container.querySelector('#btn-send-ai');
        const chipsContainer = container.querySelector('#ai-question-chips');
        const searchInput = container.querySelector('#ai-q-search');
        const categoryTabs = container.querySelectorAll('.ai-category-tab');
        const toggleBtn = container.querySelector('#btn-toggle-chips');
        const chipsWrapper = container.querySelector('#ai-chips-container');
        
        // Attach quick starter click handlers
        container.querySelectorAll('.starter-chip').forEach(btn => {
            btn.onclick = () => {
                const text = btn.innerText.trim();
                input.value = text;
                sendMessage(text);
            };
        });
        
        let currentCategory = 'All';
        let searchQuery = '';

        // Toggle questions panel
        let isChipsVisible = true;
        toggleBtn.onclick = () => {
            isChipsVisible = !isChipsVisible;
            chipsWrapper.style.display = isChipsVisible ? 'flex' : 'none';
            toggleBtn.innerHTML = isChipsVisible ? '<i class="fa-solid fa-chevron-up"></i> Hide' : '<i class="fa-solid fa-chevron-down"></i> Show 40 Questions';
        };

        // Render Question Chips function
        const renderChips = () => {
            chipsContainer.innerHTML = '';
            const filtered = components.botQuestions.filter(item => {
                const matchCat = (currentCategory === 'All' || item.category === currentCategory);
                const matchSearch = !searchQuery || item.q.toLowerCase().includes(searchQuery.toLowerCase()) || item.category.toLowerCase().includes(searchQuery.toLowerCase());
                return matchCat && matchSearch;
            });

            if (filtered.length === 0) {
                chipsContainer.innerHTML = `<div style="font-size:11px; color:var(--text-muted); padding:6px;">No questions match "${searchQuery}". Try another keyword or category.</div>`;
                return;
            }

            filtered.forEach(item => {
                const chip = document.createElement('button');
                chip.className = 'ai-question-chip';
                chip.innerHTML = `<i class="fa-solid ${item.icon}"></i> ${item.q}`;
                chip.onclick = () => {
                    input.value = item.q;
                    sendMessage(item.q);
                };
                chipsContainer.appendChild(chip);
            });
        };

        // Category tab clicks
        categoryTabs.forEach(tab => {
            tab.onclick = () => {
                categoryTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentCategory = tab.getAttribute('data-cat');
                renderChips();
            };
        });

        // Search input event
        searchInput.oninput = (e) => {
            searchQuery = e.target.value.trim();
            renderChips();
        };

        // Initial render of chips
        renderChips();

        // Send Message logic
        const sendMessage = async (overrideText = null) => {
            const text = (overrideText || input.value).trim();
            if (!text) return;
            
            const userBubble = document.createElement('div');
            userBubble.className = 'chat-bubble user';
            userBubble.innerText = text;
            history.appendChild(userBubble);
            history.scrollTop = history.scrollHeight;
            
            input.value = '';
            
            const loadingBubble = document.createElement('div');
            loadingBubble.className = 'chat-bubble ai';
            loadingBubble.innerHTML = `<i class="fa-solid fa-ellipsis fa-bounce"></i> Analyzing query & disaster records...`;
            history.appendChild(loadingBubble);
            history.scrollTop = history.scrollHeight;
            
            try {
                const res = await api.request(endpoint, {
                    method: 'POST',
                    body: JSON.stringify({ message: text, question: text })
                });
                
                const answerText = res.response || res.answer || "No response received.";
                loadingBubble.innerHTML = components.formatAIResponse(answerText);
            } catch (e) {
                loadingBubble.innerText = `Error: ${e.message || 'Failed to reach AI service.'}`;
            }
            history.scrollTop = history.scrollHeight;
        };
        
        sendBtn.onclick = () => sendMessage();
        input.onkeydown = (e) => {
            if (e.key === 'Enter') sendMessage();
        };
    }
};

// Auto close notify dropdowns when clicking outside
window.addEventListener('click', () => {
    const dropdown = document.getElementById('navbar-notify-dropdown');
    if (dropdown) dropdown.style.display = 'none';
});
