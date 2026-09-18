import os
import json
import random
from datetime import datetime, timedelta
import sys

# Ensure backend directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.models.core import (
    db, User, Area, Alert, SosRequest, Ngo, Mission, RescueTeam, Resource, Shelter, Hospital, NgoCapacity, AuditLog, Notification, NgoMember
)
from backend.app.config import Config

# Define 22 core Chennai hubs with realistic parameters
CHENNAI_HUBS = [
    {"name": "Velachery", "zone": "Zone 13 Adyar", "lat": 12.9802, "lng": 80.2228, "elev": 2.0, "water_dist": 200, "hist_freq": 0.85, "pop_density": 8000},
    {"name": "Pallikaranai", "zone": "Zone 14 Perungudi", "lat": 12.9349, "lng": 80.2137, "elev": 1.5, "water_dist": 50, "hist_freq": 0.95, "pop_density": 4500},
    {"name": "T. Nagar", "zone": "Zone 10 Kodambakkam", "lat": 13.0418, "lng": 80.2341, "elev": 3.5, "water_dist": 400, "hist_freq": 0.75, "pop_density": 15000},
    {"name": "Adyar", "zone": "Zone 13 Adyar", "lat": 13.0063, "lng": 80.2574, "elev": 4.0, "water_dist": 150, "hist_freq": 0.65, "pop_density": 9000},
    {"name": "Mylapore", "zone": "Zone 9 Teynampet", "lat": 13.0333, "lng": 80.2685, "elev": 6.0, "water_dist": 500, "hist_freq": 0.30, "pop_density": 12000},
    {"name": "Nungambakkam", "zone": "Zone 10 Kodambakkam", "lat": 13.0569, "lng": 80.2425, "elev": 5.5, "water_dist": 800, "hist_freq": 0.40, "pop_density": 10000},
    {"name": "Guindy", "zone": "Zone 13 Adyar", "lat": 13.0067, "lng": 80.2206, "elev": 9.0, "water_dist": 600, "hist_freq": 0.15, "pop_density": 5000},
    {"name": "Vyasarpadi", "zone": "Zone 6 Thiru. Vi. Ka. Nagar", "lat": 13.1141, "lng": 80.2562, "elev": 1.8, "water_dist": 300, "hist_freq": 0.88, "pop_density": 14000},
    {"name": "Saidapet", "zone": "Zone 10 Kodambakkam", "lat": 13.0213, "lng": 80.2231, "elev": 3.0, "water_dist": 100, "hist_freq": 0.70, "pop_density": 11000},
    {"name": "Madipakkam", "zone": "Zone 14 Perungudi", "lat": 12.9647, "lng": 80.2072, "elev": 2.5, "water_dist": 350, "hist_freq": 0.80, "pop_density": 6500},
    {"name": "Besant Nagar", "zone": "Zone 13 Adyar", "lat": 13.0003, "lng": 80.2667, "elev": 4.5, "water_dist": 100, "hist_freq": 0.45, "pop_density": 7000},
    {"name": "Triplicane", "zone": "Zone 9 Teynampet", "lat": 13.0587, "lng": 80.2721, "elev": 3.0, "water_dist": 200, "hist_freq": 0.50, "pop_density": 16000},
    {"name": "Royapettah", "zone": "Zone 9 Teynampet", "lat": 13.0513, "lng": 80.2612, "elev": 4.0, "water_dist": 700, "hist_freq": 0.35, "pop_density": 13000},
    {"name": "Anna Nagar", "zone": "Zone 8 Anna Nagar", "lat": 13.0850, "lng": 80.2101, "elev": 7.0, "water_dist": 1000, "hist_freq": 0.20, "pop_density": 9500},
    {"name": "Ambattur", "zone": "Zone 7 Ambattur", "lat": 13.1143, "lng": 80.1548, "elev": 12.0, "water_dist": 800, "hist_freq": 0.10, "pop_density": 6000},
    {"name": "Sholinganallur", "zone": "Zone 15 Sholinganallur", "lat": 12.9010, "lng": 80.2279, "elev": 2.0, "water_dist": 150, "hist_freq": 0.75, "pop_density": 4000},
    {"name": "Tondiarpet", "zone": "Zone 4 Tondiarpet", "lat": 13.1256, "lng": 80.2869, "elev": 3.0, "water_dist": 300, "hist_freq": 0.55, "pop_density": 15000},
    {"name": "Royapuram", "zone": "Zone 5 Royapuram", "lat": 13.1095, "lng": 80.2941, "elev": 2.5, "water_dist": 100, "hist_freq": 0.60, "pop_density": 14500},
    {"name": "Perungudi", "zone": "Zone 14 Perungudi", "lat": 12.9654, "lng": 80.2461, "elev": 2.2, "water_dist": 100, "hist_freq": 0.80, "pop_density": 5500},
    {"name": "Madhavaram", "zone": "Zone 3 Madhavaram", "lat": 13.1489, "lng": 80.2306, "elev": 5.0, "water_dist": 900, "hist_freq": 0.35, "pop_density": 7000},
    {"name": "Manali", "zone": "Zone 2 Manali", "lat": 13.1668, "lng": 80.2608, "elev": 3.0, "water_dist": 400, "hist_freq": 0.65, "pop_density": 3000},
    {"name": "Thiruvottiyur", "zone": "Zone 1 Thiruvottiyur", "lat": 13.1612, "lng": 80.3019, "elev": 2.0, "water_dist": 50, "hist_freq": 0.70, "pop_density": 8500}
]

def calculate_risk_score(elev, water_dist, hist_freq, pop_density, rainfall=0, sos_density=0):
    # Normalize values to 0.0 - 1.0 range for weighted scoring
    # Elevation factor: lower elevation = higher risk. Max elevation 15m.
    elev_factor = max(0.0, min(1.0, (15.0 - elev) / 15.0))
    
    # Proximity to water: closer = higher risk. Max distance 1500m.
    water_factor = max(0.0, min(1.0, (1500.0 - water_dist) / 1500.0))
    
    # Population density factor: max 20000.
    pop_factor = max(0.0, min(1.0, pop_density / 20000.0))
    
    # Current rainfall factor: max 100mm/hr.
    rain_factor = max(0.0, min(1.0, rainfall / 100.0))
    
    # SOS density factor: max 5 active.
    sos_factor = max(0.0, min(1.0, sos_density / 5.0))
    
    # Weights (summing up to 1.0)
    w_hist = 0.25
    w_elev = 0.20
    w_pop = 0.15
    w_water = 0.15
    w_rain = 0.15
    w_sos = 0.10
    
    score = (w_hist * hist_freq + 
             w_elev * elev_factor + 
             w_pop * pop_factor + 
             w_water * water_factor + 
             w_rain * rain_factor + 
             w_sos * sos_factor)
             
    return min(1.0, max(0.0, score))

def get_risk_level(score):
    if score < 0.25:
        return 'Low'
    elif score < 0.50:
        return 'Medium'
    elif score < 0.75:
        return 'High'
    else:
        return 'Critical'

def generate_areas():
    areas_list = []
    
    # We want exactly 426 areas.
    # We will generate 19 sub-areas around each of our 22 hubs (22 * 19 = 418), 
    # plus 8 additional central hub sectors to make it exactly 426.
    
    total_needed = 426
    sub_count_per_hub = 19
    extras_needed = total_needed - (len(CHENNAI_HUBS) * sub_count_per_hub)  # 426 - 418 = 8
    
    area_index = 1
    
    for hub_idx, hub in enumerate(CHENNAI_HUBS):
        # Determine number of sub-areas for this hub
        num_subs = sub_count_per_hub
        if hub_idx < extras_needed:
            num_subs += 1
            
        for s in range(num_subs):
            # Create sub-area details with slight variation
            if s == 0:
                # The primary hub area itself
                name = f"{hub['name']} Main Sector"
                lat = hub['lat']
                lng = hub['lng']
            else:
                name = f"{hub['name']} Sector {chr(64 + s)}"
                # Apply slight offset to lat/lng (within ~500m - 1km)
                lat = hub['lat'] + random.uniform(-0.006, 0.006)
                lng = hub['lng'] + random.uniform(-0.006, 0.006)
                
            # Randomize parameters slightly based on base hub values
            elev = max(0.5, hub['elev'] + random.uniform(-1.0, 1.0))
            water_dist = max(10, hub['water_dist'] + random.uniform(-100, 100))
            hist_freq = max(0.0, min(1.0, hub['hist_freq'] + random.uniform(-0.1, 0.1)))
            pop_density = max(1000, hub['pop_density'] + int(random.uniform(-1500, 1500)))
            
            # Initial rainfall
            rainfall = 0
            if hist_freq > 0.75 and random.random() > 0.5:
                # Seed some initial high rainfall in flood prone areas to make the dashboard dynamic
                rainfall = random.uniform(20.0, 65.0)
                
            score = calculate_risk_score(elev, water_dist, hist_freq, pop_density, rainfall=rainfall)
            level = get_risk_level(score)
            
            # Calculate mock boundary GeoJSON (a small bounding polygon around the point)
            # A 6-sided hexagon or 4-sided rectangle
            r = 0.0025 # radius of polygon in degrees
            coords = [
                [lng - r, lat - r],
                [lng + r, lat - r],
                [lng + r, lat + r],
                [lng - r, lat + r],
                [lng - r, lat - r] # closed
            ]
            geojson = {
                "type": "Feature",
                "properties": {
                    "id": area_index,
                    "name": name,
                    "zone": hub['zone'],
                    "risk_level": level,
                    "risk_score": round(score, 4)
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            }
            
            areas_list.append({
                "id": area_index,
                "area_name": name,
                "zone": hub['zone'],
                "latitude": lat,
                "longitude": lng,
                "boundary_geojson": json.dumps(geojson),
                "population": int(pop_density * random.uniform(2.5, 4.0)),
                "risk_level": level,
                "risk_score": score,
                "elevation": elev,
                "water_distance": water_dist,
                "hist_frequency": hist_freq,
                "rainfall_intensity": rainfall
            })
            area_index += 1
            
    return areas_list

def seed_db(app):
    print("Generating Chennai 426 areas seed data...")
    areas_data = generate_areas()
    
    # Generate unified GeoJSON file for frontend
    geojson_features = []
    for area in areas_data:
        geojson_features.append(json.loads(area['boundary_geojson']))
        
    geojson_root = {
        "type": "FeatureCollection",
        "features": geojson_features
    }
    
    data_dir = os.path.dirname(os.path.abspath(__file__))
    geojson_path = os.path.join(data_dir, 'chennai_areas.geojson')
    with open(geojson_path, 'w') as f:
        json.dump(geojson_root, f, indent=2)
    print(f"Generated Chennai GeoJSON file at: {geojson_path}")
    
    with app.app_context():
        # Clear existing tables to avoid duplicate keys on seed
        db.reflect()
        db.drop_all()
        db.create_all()
        
        # 1. Insert Areas
        print("Inserting 426 areas into database...")
        db_areas = []
        for area_info in areas_data:
            a = Area(
                id=area_info['id'],
                area_name=area_info['area_name'],
                zone=area_info['zone'],
                latitude=area_info['latitude'],
                longitude=area_info['longitude'],
                boundary_geojson=area_info['boundary_geojson'],
                population=area_info['population'],
                risk_level=area_info['risk_level'],
                risk_score=area_info['risk_score'],
                elevation=area_info['elevation'],
                water_distance=area_info['water_distance'],
                hist_frequency=area_info['hist_frequency'],
                rainfall_intensity=area_info['rainfall_intensity']
            )
            db.session.add(a)
            db_areas.append(a)
        db.session.commit()
        print("Successfully inserted areas!")

        # 2. Insert Default Users
        print("Inserting default accounts...")
        users = [
            {"name": "State Disaster Admin", "email": "admin@gov.in", "phone": "9876543210", "role": "gov", "pass": "admin123"},
            {"name": "District Officer Chennai", "email": "officer@gov.in", "phone": "9876543211", "role": "gov", "pass": "officer123"},
            {"name": "Disaster Analyst", "email": "analyst@gov.in", "phone": "9876543212", "role": "gov", "pass": "analyst123"},
            {"name": "Raman Nathan (Citizen)", "email": "citizen@test.com", "phone": "9123456789", "role": "citizen", "pass": "citizen123"},
            {"name": "Priya Swaminathan (Citizen)", "email": "priya@test.com", "phone": "9123456788", "role": "citizen", "pass": "citizen123"},
            {"name": "Chennai Rescue Force", "email": "ngo@test.org", "phone": "8877665544", "role": "ngo", "pass": "ngo123"},
            {"name": "Red Cross Tamil Nadu", "email": "redcross@test.org", "phone": "8877665545", "role": "ngo", "pass": "ngo123"}
        ]
        
        db_users = {}
        for u_info in users:
            u = User(
                name=u_info['name'],
                email=u_info['email'],
                phone=u_info['phone'],
                role=u_info['role']
            )
            u.set_password(u_info['pass'])
            db.session.add(u)
            db.session.flush() # Populate ID
            db_users[u_info['email']] = u
        db.session.commit()
        
        # 3. Create NGO Profiles
        print("Creating NGO Profiles...")
        ngo_profiles = [
            {"user_email": "ngo@test.org", "org_name": "Chennai Rescue Force", "reg": "NGO/2026/CH/9981", "capacity": 25, "contact": "+91 9988776655"},
            {"user_email": "redcross@test.org", "org_name": "Red Cross Tamil Nadu", "reg": "NGO/2026/TN/0432", "capacity": 50, "contact": "+91 9900881122"}
        ]
        
        db_ngos = {}
        for ngo_info in ngo_profiles:
            n = Ngo(
                user_id=db_users[ngo_info['user_email']].id,
                org_name=ngo_info['org_name'],
                registration_number=ngo_info['reg'],
                verified=True,
                contact_info=ngo_info['contact'],
                capacity=ngo_info['capacity']
            )
            db.session.add(n)
            db.session.flush()
            db_ngos[ngo_info['user_email']] = n
            
            # Create capacity model
            cap = NgoCapacity(
                ngo_id=n.id,
                active_missions_count=0,
                max_concurrent_missions=5
            )
            db.session.add(cap)
            
            # Create some teams for the NGO
            for i in range(1, 4):
                t = RescueTeam(
                    ngo_id=n.id,
                    team_name=f"{n.org_name} Team {i}",
                    members_count=random.randint(5, 12),
                    status="available"
                )
                db.session.add(t)
        db.session.commit()

        # Seed 20,000 NGO members
        seed_ngo_members(db_ngos)

        # 4. Insert Shelters & Hospitals
        print("Inserting Shelters & Hospitals...")
        for hub in CHENNAI_HUBS:
            # Find seeded area matching this hub's center name
            match_area = Area.query.filter(Area.area_name.like(f"{hub['name']}%")).first()
            if match_area:
                # Add Shelter
                s = Shelter(
                    name=f"{hub['name']} Emergency Relief Center",
                    area_id=match_area.id,
                    latitude=hub['lat'] + 0.001,
                    longitude=hub['lng'] - 0.001,
                    capacity=random.choice([150, 200, 300, 500]),
                    current_occupancy=random.randint(0, 40),
                    contact=f"+91 44 2200 {random.randint(1000, 9999)}"
                )
                db.session.add(s)
                
                # Add Hospital
                h = Hospital(
                    name=f"{hub['name']} General Hospital",
                    area_id=match_area.id,
                    latitude=hub['lat'] - 0.001,
                    longitude=hub['lng'] + 0.001,
                    contact=f"+91 44 2400 {random.randint(1000, 9999)}",
                    beds_available=random.randint(5, 75)
                )
                db.session.add(h)
                
                # Add Resources
                for r_type in ['food', 'medical', 'boats', 'shelter', 'personnel']:
                    res = Resource(
                        area_id=match_area.id,
                        resource_type=r_type,
                        quantity_available=random.randint(10, 150),
                        quantity_required=random.randint(20, 200)
                    )
                    db.session.add(res)
                    
        db.session.commit()
        
        # 5. Insert some initial alerts
        print("Inserting default active alerts...")
        # Alert 1: Flood Alert in Velachery
        velachery_area = Area.query.filter(Area.area_name.like("Velachery%")).first()
        if velachery_area:
            a1 = Alert(
                title="Severe Inundation Warning — Low-lying Areas",
                description="Heavy rainfall has caused waterlogging up to 2 feet in several streets. Residents are advised to stay indoors or move to the nearest emergency relief shelter.",
                disaster_type="Flood",
                severity="Severe",
                area_id=velachery_area.id,
                issued_by=db_users['admin@gov.in'].id,
                issued_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=2)
            )
            db.session.add(a1)
            
        # Alert 2: City wide Heatwave Alert
        a2 = Alert(
            title="City-Wide Heatwave & Dehydration Advisory",
            description="Temperatures expected to touch 41°C. Keep hydrated and avoid direct sunlight exposure between 11:00 AM and 3:30 PM.",
            disaster_type="Heatwave",
            severity="Moderate",
            area_id=None, # City-wide
            issued_by=db_users['officer@gov.in'].id,
            issued_at=datetime.utcnow() - timedelta(hours=6),
            expires_at=datetime.utcnow() + timedelta(hours=18)
        )
        db.session.add(a2)
        
        # 6. Insert some sample SOS Requests to populate the queue
        print("Inserting sample SOS requests...")
        # SOS 1: Citizen 1 trapped in Velachery
        if velachery_area:
            sos1 = SosRequest(
                citizen_id=db_users['citizen@test.com'].id,
                area_id=velachery_area.id,
                latitude=velachery_area.latitude + 0.0004,
                longitude=velachery_area.longitude - 0.0003,
                emergency_type="Flood",
                people_affected=4,
                medical_needs="Elderly person requires insulin and immediate medical evacuation.",
                description="Water has entered the ground floor. We are on the first floor terrace without power.",
                status="pending",
                priority_score=0.0, # Will be calculated by service
                created_at=datetime.utcnow() - timedelta(minutes=45)
            )
            db.session.add(sos1)
            
        # SOS 2: Citizen 2 trapped in Pallikaranai
        palli_area = Area.query.filter(Area.area_name.like("Pallikaranai%")).first()
        if palli_area:
            sos2 = SosRequest(
                citizen_id=db_users['priya@test.com'].id,
                area_id=palli_area.id,
                latitude=palli_area.latitude - 0.0002,
                longitude=palli_area.longitude + 0.0005,
                emergency_type="Trapped",
                people_affected=7,
                medical_needs="Child with high fever.",
                description="Roads flooded, no boats available. Need food and medical support.",
                status="pending",
                priority_score=0.0, # Will be calculated
                created_at=datetime.utcnow() - timedelta(minutes=15)
            )
            db.session.add(sos2)
            
        db.session.commit()
        
        # Trigger priority scoring calculations
        print("Calculating priorities for sample SOS...")
        from backend.app.services.sos_priority import calculate_sos_priority
        pending_soses = SosRequest.query.all()
        for sos in pending_soses:
            sos.priority_score = calculate_sos_priority(sos)
        db.session.commit()
        
        # Seed initial Audit logs & notifications
        print("Inserting initial audit logs & notification feeds...")
        admin_user = db_users['admin@gov.in']
        ngo_user = db_users['ngo@test.org']
        citizen_user = db_users['citizen@test.com']

        # Add Audit log
        log1 = AuditLog(
            actor_id=admin_user.id,
            action_type="ngo_verify",
            target_type="Ngo",
            target_id=db_ngos['ngo@test.org'].id,
            details_json="Verified Chennai Rescue Force registration and capacity load specifications."
        )
        db.session.add(log1)

        # Add Notification
        n1 = Notification(
            user_id=ngo_user.id,
            title="Account Verified",
            body="Welcome to Disaster Shield AI. Your organization profile is now fully approved for dispatch operations.",
            severity="info",
            read=False
        )
        n2 = Notification(
            user_id=citizen_user.id,
            title="Extreme Rainfall Alert",
            body="Heavy water stagnancy reported around Adyar river delta sectors. Avoid low-lying bypass subways.",
            severity="high",
            read=False
        )
        db.session.add(n1)
        db.session.add(n2)
        db.session.commit()
        
        print("Seeding database complete!")

def seed_ngo_members(db_ngos):
    print("Generating 20,000 NGO members...")
    skills = ['rescue', 'food distribution', 'medical support', 'shelter management', 'transportation', 'communication', 'logistics', 'disaster response']
    regions = ['Velachery', 'Pallikaranai', 'T. Nagar', 'Adyar', 'Mylapore', 'Nungambakkam', 'Guindy', 'Vyasarpadi', 'Saidapet', 'Madipakkam', 'Besant Nagar', 'Triplicane', 'Royapettah', 'Anna Nagar', 'Ambattur', 'Sholinganallur', 'Tondiarpet', 'Royapuram', 'Perungudi', 'Madhavaram', 'Manali', 'Thiruvottiyur']
    names_first = ['Vijay', 'Anand', 'Rajesh', 'Suresh', 'Karthik', 'Raman', 'Arun', 'Sanjay', 'Manoj', 'Deepak', 'Ganesh', 'Priya', 'Swati', 'Lakshmi', 'Ravi', 'Hari', 'Venkat', 'Babu', 'Murugan', 'Kumar']
    names_last = ['Nathan', 'Raghavan', 'Swaminathan', 'Rao', 'Iyer', 'Pillai', 'Rajan', 'Sekhar', 'Prasad', 'Naidu', 'Chettiar', 'Balaji', 'Das', 'Sen', 'Menon', 'Nair', 'Sharma', 'Reddy', 'Patel', 'Joshi']

    ngo_ids = [ngo.id for ngo in db_ngos.values()]
    if not ngo_ids:
         return
         
    members_to_insert = []
    # To keep it performant and diverse, generate 20000 records
    for idx in range(1, 20001):
        ngo_id = ngo_ids[idx % len(ngo_ids)]
        name = f"{random.choice(names_first)} {random.choice(names_last)} {idx}"
        age = random.randint(18, 60)
        phone = f"9{random.randint(100000000, 999999999)}"
        region = random.choice(regions)
        skill = random.choice(skills)
        availability = random.choice(['available', 'available', 'available', 'active', 'offline'])
        current_assignment = None
        if availability == 'active':
             current_assignment = f"Mission #{random.randint(1, 10)}"
        
        members_to_insert.append({
            "ngo_id": ngo_id,
            "name": name,
            "age": age,
            "phone": phone,
            "region": region,
            "skill": skill,
            "availability": availability,
            "current_assignment": current_assignment,
            "status": "Active"
        })
        
        # Batch insert every 5000 records to keep memory footprint low
        if len(members_to_insert) >= 5000:
            db.session.execute(db.insert(NgoMember), members_to_insert)
            members_to_insert = []
            print(f"Inserted {idx} members...")
            
    if members_to_insert:
        db.session.execute(db.insert(NgoMember), members_to_insert)
        print("Inserted remaining members...")
        
    db.session.commit()
    print("NGO members seeded successfully!")

if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    seed_db(app)
