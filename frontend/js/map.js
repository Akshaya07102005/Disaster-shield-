// Unified GIS Mapping Engine for Disaster Shield AI using Leaflet.js
let map;
let areasLayer;
let sosLayerGroup;
let shelterLayerGroup;
let hospitalLayerGroup;
let teamLayerGroup;

// Center on Chennai
const CHENNAI_CENTER = [13.0418, 80.2341];
const DEFAULT_ZOOM = 11.5;

function getRiskColor(level) {
    switch (level) {
        case 'Critical': return '#7F1D1D';
        case 'High':     return '#EF4444';
        case 'Medium':   return '#F59E0B';
        case 'Low':      return '#10B981';
        default:         return '#10B981';
    }
}

function initMap(mapElementId = 'map', onClickAreaCallback = null) {
    if (map) return map;
    
    // Initialize map
    map = L.map(mapElementId, {
        zoomControl: true,
        maxZoom: 18,
        minZoom: 10
    }).setView(CHENNAI_CENTER, DEFAULT_ZOOM);
    
    // Premium dark tile layer (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
    
    // Create layer groups
    sosLayerGroup = L.layerGroup().addTo(map);
    shelterLayerGroup = L.layerGroup().addTo(map);
    hospitalLayerGroup = L.layerGroup().addTo(map);
    teamLayerGroup = L.layerGroup().addTo(map);
    
    // Load Chennai Area Polygons
    loadAreas(onClickAreaCallback);
    
    return map;
}

async function loadAreas(onClickAreaCallback = null) {
    try {
        const response = await fetch('/data/chennai_areas.geojson');
        const geojsonData = await response.json();
        
        areasLayer = L.geoJSON(geojsonData, {
            style: function (feature) {
                const level = feature.properties.risk_level;
                const score = feature.properties.risk_score;
                return {
                    fillColor: getRiskColor(level),
                    weight: 1.5,
                    opacity: 0.6,
                    color: '#1E293B', // border color
                    fillOpacity: level === 'Critical' ? 0.5 : level === 'High' ? 0.4 : level === 'Medium' ? 0.3 : 0.15
                };
            },
            onEachFeature: function (feature, layer) {
                // Hover effect
                layer.on({
                    mouseover: function (e) {
                        const l = e.target;
                        l.setStyle({
                            weight: 3,
                            opacity: 1,
                            color: '#60A5FA',
                            fillOpacity: l.options.fillOpacity + 0.15
                        });
                        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                            l.bringToFront();
                        }
                    },
                    mouseout: function (e) {
                        areasLayer.resetStyle(e.target);
                    },
                    click: function (e) {
                        if (onClickAreaCallback) {
                            onClickAreaCallback(feature.properties);
                        } else {
                            // Default Popup
                            layer.bindPopup(`
                                <div class="popup-details">
                                    <div class="popup-title">${feature.properties.name}</div>
                                    <div class="popup-item"><span>Zone:</span> ${feature.properties.zone}</div>
                                    <div class="popup-item"><span>Risk Level:</span> <b>${feature.properties.risk_level}</b></div>
                                    <div class="popup-item"><span>Risk Score:</span> ${feature.properties.risk_score}</div>
                                </div>
                            `).openPopup();
                        }
                    }
                });
            }
        }).addTo(map);
        
    } catch (e) {
        console.error('Failed to load Chennai areas GeoJSON:', e);
    }
}

// Markers Helpers
function updateSOSMarkers(sosRequests) {
    sosLayerGroup.clearLayers();
    
    // Custom Pulsing DivIcon for SOS
    const sosIcon = L.divIcon({
        className: 'sos-marker-icon',
        html: `
            <div style="position: relative; width: 24px; height: 24px;">
                <div style="position: absolute; top: 4px; left: 4px; width: 14px; height: 14px; border-radius: 50%; background: #EF4444; border: 2px solid white; z-index: 10;"></div>
                <div style="position: absolute; width: 22px; height: 22px; border-radius: 50%; border: 3px solid #EF4444; animation: ripple 1.5s infinite ease-out; opacity: 0.8;"></div>
            </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    sosRequests.forEach(sos => {
        if (sos.status === 'resolved') return; // Don't show resolved SOS on map
        
        const priorityColor = sos.priority_score > 30 ? '#EF4444' : sos.priority_score > 15 ? '#F59E0B' : '#3B82F6';
        
        const popupContent = `
            <div class="popup-details">
                <div class="popup-title" style="color: #EF4444;"><i class="fa-solid fa-circle-exclamation"></i> Emergency SOS</div>
                <div class="popup-item"><span>Citizen:</span> ${sos.citizen_name}</div>
                <div class="popup-item"><span>Phone:</span> ${sos.citizen_phone}</div>
                <div class="popup-item"><span>Type:</span> <b>${sos.emergency_type}</b></div>
                <div class="popup-item"><span>Affected:</span> ${sos.people_affected} person(s)</div>
                <div class="popup-item"><span>Priority:</span> <b style="color: ${priorityColor};">${sos.priority_score}</b></div>
                <div class="popup-item"><span>Medical:</span> ${sos.medical_needs || 'None'}</div>
                <div class="popup-item"><span>Status:</span> <span class="user-badge" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239,68,68,0.3); color: #EF4444; padding: 2px 6px;">${sos.status.toUpperCase()}</span></div>
                <div style="margin-top: 8px; font-size: 11px; max-height: 80px; overflow-y: auto; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 4px;">
                    ${sos.description || 'No description provided.'}
                </div>
            </div>
        `;
        
        L.marker([sos.latitude, sos.longitude], { icon: sosIcon })
            .bindPopup(popupContent)
            .addTo(sosLayerGroup);
    });
}

function updateShelterMarkers(shelters) {
    shelterLayerGroup.clearLayers();
    
    // Custom blue marker for shelters
    const shelterIcon = L.divIcon({
        className: 'shelter-marker-icon',
        html: `
            <div style="display:flex; justify-content:center; align-items:center; width:30px; height:30px; border-radius:50%; background:#2563EB; border:2px solid white; color:white; font-size:12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <i class="fa-solid fa-house-chimney-medical"></i>
            </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    shelters.forEach(shelter => {
        const popupContent = `
            <div class="popup-details">
                <div class="popup-title" style="color: #60A5FA;"><i class="fa-solid fa-house-shield"></i> Shelter Active</div>
                <div class="popup-item"><span>Name:</span> ${shelter.name}</div>
                <div class="popup-item"><span>Capacity:</span> ${shelter.current_occupancy} / ${shelter.capacity}</div>
                <div class="popup-item"><span>Contact:</span> ${shelter.contact || 'N/A'}</div>
            </div>
        `;
        L.marker([shelter.latitude, shelter.longitude], { icon: shelterIcon })
            .bindPopup(popupContent)
            .addTo(shelterLayerGroup);
    });
}

function updateHospitalMarkers(hospitals) {
    hospitalLayerGroup.clearLayers();
    
    // Custom red/green cross icon for hospitals
    const hospitalIcon = L.divIcon({
        className: 'hospital-marker-icon',
        html: `
            <div style="display:flex; justify-content:center; align-items:center; width:30px; height:30px; border-radius:50%; background:#059669; border:2px solid white; color:white; font-size:12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <i class="fa-solid fa-square-h"></i>
            </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    hospitals.forEach(hosp => {
        const popupContent = `
            <div class="popup-details">
                <div class="popup-title" style="color: #34D399;"><i class="fa-solid fa-hospital"></i> Medical Hospital</div>
                <div class="popup-item"><span>Name:</span> ${hosp.name}</div>
                <div class="popup-item"><span>Beds Available:</span> <b>${hosp.beds_available}</b></div>
                <div class="popup-item"><span>Contact:</span> ${hosp.contact || 'N/A'}</div>
            </div>
        `;
        L.marker([hosp.latitude, hosp.longitude], { icon: hospitalIcon })
            .bindPopup(popupContent)
            .addTo(hospitalLayerGroup);
    });
}

// Live tracking markers for NGO rescue squads
const activeTeamMarkers = {}; // Keep track to animate updates smoothly

function updateTeamMarkers(teams) {
    // We update existing or add new
    teams.forEach(team => {
        if (team.current_lat === null || team.current_lng === null) return;
        
        const popupContent = `
            <div class="popup-details">
                <div class="popup-title" style="color: #60A5FA;"><i class="fa-solid fa-truck-medical"></i> Rescue Team Active</div>
                <div class="popup-item"><span>Team Name:</span> ${team.team_name}</div>
                <div class="popup-item"><span>NGO:</span> ${team.ngo_name}</div>
                <div class="popup-item"><span>Members:</span> ${team.members_count} members</div>
                <div class="popup-item"><span>Status:</span> <span class="user-badge" style="background: rgba(96,165,250,0.15); border-color: rgba(96,165,250,0.3); color: #60A5FA; padding: 2px 6px;">${team.status.toUpperCase()}</span></div>
            </div>
        `;
        
        const teamIcon = L.divIcon({
            className: 'team-marker-icon',
            html: `
                <div style="display:flex; justify-content:center; align-items:center; width:32px; height:32px; border-radius:50%; background:#7C3AED; border:2.5px solid white; color:white; font-size:12px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); animation: teamPulsate 2s infinite;">
                    <i class="fa-solid fa-people-group"></i>
                </div>
            `,
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });
        
        if (activeTeamMarkers[team.id]) {
            // Smooth move
            activeTeamMarkers[team.id].setLatLng([team.current_lat, team.current_lng]);
            activeTeamMarkers[team.id].setPopupContent(popupContent);
        } else {
            const marker = L.marker([team.current_lat, team.current_lng], { icon: teamIcon })
                .bindPopup(popupContent)
                .addTo(teamLayerGroup);
            activeTeamMarkers[team.id] = marker;
        }
    });
    
    // Clean up offline/removed teams
    const teamIdsInUpdate = teams.map(t => t.id);
    Object.keys(activeTeamMarkers).forEach(tid => {
        if (!teamIdsInUpdate.includes(parseInt(tid))) {
            map.removeLayer(activeTeamMarkers[tid]);
            delete activeTeamMarkers[tid];
        }
    });
}

// Toggle Layers
function toggleLayer(layerName, show) {
    switch (layerName) {
        case 'risk':
            if (show) map.addLayer(areasLayer); else map.removeLayer(areasLayer);
            break;
        case 'sos':
            if (show) map.addLayer(sosLayerGroup); else map.removeLayer(sosLayerGroup);
            break;
        case 'shelters':
            if (show) map.addLayer(shelterLayerGroup); else map.removeLayer(shelterLayerGroup);
            break;
        case 'hospitals':
            if (show) map.addLayer(hospitalLayerGroup); else map.removeLayer(hospitalLayerGroup);
            break;
        case 'teams':
            if (show) map.addLayer(teamLayerGroup); else map.removeLayer(teamLayerGroup);
            break;
    }
}
