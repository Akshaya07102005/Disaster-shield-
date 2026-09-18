import os
import unittest
import json
import sys

# Ensure project root is in search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app, db
from backend.app.models.core import User, Area, Alert, SosRequest, Ngo, Mission, RescueTeam, Resource, Shelter, Hospital
from backend.app.services.sos_priority import calculate_sos_priority
from backend.app.services.risk_engine import calculate_area_risk_score, get_risk_classification
from backend.app.services.ai_assistant import match_query

class DisasterShieldTestCase(unittest.TestCase):
    
    def setUp(self):
        # Override config for testing (in-memory SQLite)
        class TestConfig:
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            SECRET_KEY = 'test-secret'
            JWT_SECRET_KEY = 'test-jwt-secret'
            JWT_TOKEN_LOCATION = ['headers']
            JWT_COOKIE_CSRF_PROTECT = False
            UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'test_reports'))
            
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        db.create_all()
        self.seed_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def seed_test_data(self):
        # Create users
        self.gov_user = User(name="Gov Admin", email="admin@gov.in", phone="9876543210", role="gov")
        self.gov_user.set_password("admin123")
        
        self.citizen_user = User(name="Citizen Raman", email="citizen@test.com", phone="9123456789", role="citizen")
        self.citizen_user.set_password("citizen123")
        
        self.ngo_user = User(name="Rescue NGO", email="ngo@test.org", phone="8877665544", role="ngo")
        self.ngo_user.set_password("ngo123")
        
        db.session.add_all([self.gov_user, self.citizen_user, self.ngo_user])
        db.session.commit()
        
        # Create NGO profile
        self.ngo = Ngo(
            user_id=self.ngo_user.id,
            org_name="Chennai Rescue Force",
            registration_number="NGO/2026/001",
            verified=True,
            capacity=10
        )
        db.session.add(self.ngo)
        
        # Create Area
        self.area = Area(
            id=1,
            area_name="Velachery Main Sector",
            zone="Zone 13 Adyar",
            latitude=12.9802,
            longitude=80.2228,
            population=15000,
            risk_level="Medium",
            risk_score=0.4,
            elevation=2.0,
            water_distance=200.0,
            hist_frequency=0.8,
            rainfall_intensity=0.0
        )
        self.shelter = Shelter(
            id=1,
            name="Velachery Relief Camp",
            area_id=1,
            latitude=12.9810,
            longitude=80.2230,
            capacity=200,
            current_occupancy=20,
            contact="9876500001"
        )
        
        self.hospital = Hospital(
            id=1,
            name="Velachery Community Hospital",
            area_id=1,
            latitude=12.9820,
            longitude=80.2240,
            contact="044-22446688",
            beds_available=15
        )
        
        db.session.add_all([self.area, self.shelter, self.hospital])
        db.session.commit()


    def get_jwt_header(self, email, password, client=None):
        if client is None:
            client = self.client
        if hasattr(client, 'cookie_jar') and client.cookie_jar:
            client.cookie_jar.clear()
        res = client.post('/api/auth/login', json={
            "email": email,
            "password": password
        })
        data = json.loads(res.data)
        if hasattr(client, 'cookie_jar') and client.cookie_jar:
            client.cookie_jar.clear()
        return {"Authorization": f"Bearer {data['access_token']}"}


    def test_auth_flow(self):
        # Register Citizen
        res = self.client.post('/api/auth/register', json={
            "name": "New Citizen",
            "email": "new@test.com",
            "phone": "9998887770",
            "password": "password123",
            "role": "citizen"
        })
        self.assertEqual(res.status_code, 201)
        
        # Register NGO
        res = self.client.post('/api/auth/register', json={
            "name": "New NGO",
            "email": "newngo@test.org",
            "phone": "9998887771",
            "password": "password123",
            "role": "ngo",
            "org_name": "Saviors TN",
            "registration_number": "NGO/2026/002",
            "capacity": 15
        })
        self.assertEqual(res.status_code, 201)
        
        # Login Verification
        res = self.client.post('/api/auth/login', json={
            "email": "admin@gov.in",
            "password": "admin123"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "gov")

    def test_risk_calculations(self):
        # Test math engine for low-lying area with no rain (evaluates to High due to 2m elevation and 200m water proximity)
        score = calculate_area_risk_score(self.area)
        level = get_risk_classification(score)
        self.assertEqual(level, 'High')
        
        # Increase rain and check
        self.area.rainfall_intensity = 95.0 # extreme rain
        score_rain = calculate_area_risk_score(self.area)
        level_rain = get_risk_classification(score_rain)
        self.assertTrue(score_rain > score)
        self.assertEqual(level_rain, 'Critical')

    def test_sos_prioritization(self):
        # Create SOS request
        sos = SosRequest(
            citizen_id=self.citizen_user.id,
            area_id=self.area.id,
            latitude=12.9802,
            longitude=80.2228,
            emergency_type="Flood",
            people_affected=5,
            medical_needs="Critical insulin patient",
            description="Water stagnating fast"
        )
        # Mock relation
        sos.area = self.area
        
        priority = calculate_sos_priority(sos)
        # People affected = 5 * 2 = 10
        # Medical needs (critical keyword) = 15
        # Area risk score (0.4 * 10) = 4
        # Total = 10 + 15 + 4 = 29
        self.assertEqual(priority, 29.0)

    def test_gov_endpoints_rbac(self):
        # Citizen try to hit gov route -> should return 403
        citizen_client = self.app.test_client()
        citizen_headers = self.get_jwt_header("citizen@test.com", "citizen123", client=citizen_client)
        res = citizen_client.get('/api/gov/dashboard', headers=citizen_headers)
        self.assertEqual(res.status_code, 403)
        
        # Gov hit gov route -> should return 200
        gov_headers = self.get_jwt_header("admin@gov.in", "admin123")
        res = self.client.get('/api/gov/dashboard', headers=gov_headers)
        self.assertEqual(res.status_code, 200)

    def test_ai_intent_matching(self):
        # Test area query match
        matched, answer = match_query("What is the current risk level in Velachery?", self.gov_user)
        self.assertTrue(matched)
        self.assertIn("Velachery Main Sector", answer)
        
        # Test SOS query match
        matched_sos, answer_sos = match_query("How many pending SOS?", self.gov_user)
        self.assertTrue(matched_sos)
        self.assertIn("City-Wide SOS Statistics", answer_sos)

    def test_citizen_sos_endpoint(self):
        citizen_headers = self.get_jwt_header("citizen@test.com", "citizen123")
        res = self.client.post('/api/citizen/sos', json={
            "latitude": 12.9802,
            "longitude": 80.2228,
            "emergency_type": "Flood",
            "people_affected": 2,
            "medical_needs": "Insulin required",
            "description": "Rising waters"
        }, headers=citizen_headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn("sos", data)
        self.assertEqual(data["sos"]["emergency_type"], "Flood")

    def test_v2_advanced_features(self):
        # 1. Test KPI Strip
        gov_headers = self.get_jwt_header("admin@gov.in", "admin123")
        res = self.client.get('/api/gov/kpis', headers=gov_headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("active_sos", data)
        self.assertIn("resources_deployed", data)

        # 2. Test Family Group Add/Fetch (using separate citizen client)
        citizen_client = self.app.test_client()
        citizen_headers = self.get_jwt_header("citizen@test.com", "citizen123", client=citizen_client)
        res_post = citizen_client.post('/api/citizen/family-group', json={
            "member_name": "Vijay Nathan",
            "member_phone": "9944332211",
            "status": "safe"
        }, headers=citizen_headers)
        self.assertEqual(res_post.status_code, 201)
        
        res_get = citizen_client.get('/api/citizen/family-group', headers=citizen_headers)
        self.assertEqual(res_get.status_code, 200)
        members = json.loads(res_get.data)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["member_name"], "Vijay Nathan")

        # 3. Test AI Resource Optimizer Suggestions
        res_opt = self.client.post('/api/gov/resources/optimize', json={}, headers=gov_headers)
        self.assertEqual(res_opt.status_code, 200)
        opt_data = json.loads(res_opt.data)
        self.assertIn("suggestions", opt_data)

    def test_v3_public_and_auth_features(self):
        # 1. Test public status endpoint
        res = self.client.get('/api/public/status')
        self.assertEqual(res.status_code, 200)
        status = json.loads(res.data)
        self.assertEqual(status["total_mapped_sectors"], 1)
        self.assertIn("critical_areas", status)
        self.assertIn("resolved_sos_this_month", status)

        # 2. Test public alerts ticker
        res_alerts = self.client.get('/api/public/alerts')
        self.assertEqual(res_alerts.status_code, 200)
        alerts = json.loads(res_alerts.data)
        self.assertEqual(type(alerts), list)

        # 3. Test public areas selector list
        res_areas = self.client.get('/api/public/areas')
        self.assertEqual(res_areas.status_code, 200)
        areas = json.loads(res_areas.data)
        self.assertEqual(len(areas), 1)
        self.assertEqual(areas[0]["area_name"], "Velachery Main Sector")

        # 4. Test self-registration block for government accounts
        res_gov_reg = self.client.post('/api/auth/register', json={
            "name": "Hack Gov Admin",
            "email": "hackedgov@gov.in",
            "phone": "9000111222",
            "password": "hackpassword",
            "role": "gov"
        })
        self.assertEqual(res_gov_reg.status_code, 403)
        self.assertIn("cannot be self-registered", json.loads(res_gov_reg.data)["message"])

        # 5. Test citizen registration with home area
        res_cit_reg = self.client.post('/api/auth/register', json={
            "name": "Local Citizen",
            "email": "new_cit@test.com",
            "phone": "9012345678",
            "password": "citpassword",
            "role": "citizen",
            "home_area_id": 1
        })
        self.assertEqual(res_cit_reg.status_code, 201)
        # Verify in DB
        user = User.query.filter_by(email="new_cit@test.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.home_area_id, 1)

        # 6. Test NGO registration and pending verification
        res_ngo_reg = self.client.post('/api/auth/register', json={
            "name": "NGO Contact",
            "email": "new_ngo@test.org",
            "phone": "9898765432",
            "password": "ngopassword",
            "role": "ngo",
            "org_name": "Test NGO Union",
            "registration_number": "NGO/REG/TEST/999",
            "capacity": 12
        })
        self.assertEqual(res_ngo_reg.status_code, 201)
        ngo = Ngo.query.filter_by(registration_number="NGO/REG/TEST/999").first()
        self.assertIsNotNone(ngo)
        self.assertFalse(ngo.verified)

    def test_v4_advanced_weather_and_simulation(self):
        gov_headers = self.get_jwt_header("admin@gov.in", "admin123")

        # 1. Test POST /api/gov/ai/weather-report
        res = self.client.post('/api/gov/ai/weather-report', headers=gov_headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("report_id", data)
        self.assertIn("summary", data)
        self.assertIn("file_path", data)
        
        report_id = data["report_id"]
        pdf_path = data["file_path"]

        # 2. Test GET /api/gov/ai/weather-report/<id>/pdf
        res_pdf = self.client.get(f'/api/gov/ai/weather-report/{report_id}/pdf', headers=gov_headers)
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, 'application/pdf')

        # 3. Test POST /api/gov/test/simulate-sos
        res_sim = self.client.post('/api/gov/test/simulate-sos', json={
            "area_id": 1,
            "emergency_type": "Flood"
        }, headers=gov_headers)
        self.assertEqual(res_sim.status_code, 201)
        sim_data = json.loads(res_sim.data)
        self.assertEqual(sim_data["is_test_data"], True)
        self.assertEqual(sim_data["emergency_type"], "Flood")

        # 4. Test POST /api/gov/test/seed
        res_seed = self.client.post('/api/gov/test/seed', headers=gov_headers)
        self.assertEqual(res_seed.status_code, 201)
        seed_data = json.loads(res_seed.data)
        self.assertIn("seeded_sos_count", seed_data)
        self.assertEqual(seed_data["seeded_sos_count"], 3)

        # 5. Test POST /api/gov/test/purge
        res_purge = self.client.post('/api/gov/test/purge', headers=gov_headers)
        self.assertEqual(res_purge.status_code, 200)
        purge_data = json.loads(res_purge.data)
        self.assertIn("deleted_sos_count", purge_data)
        self.assertGreaterEqual(purge_data["deleted_sos_count"], 4) # 1 sim + 3 seeded

    def test_v5_portal_starter_questions_and_ai(self):
        gov_headers = self.get_jwt_header("admin@gov.in", "admin123")
        ngo_headers = self.get_jwt_header("ngo@test.org", "ngo123")
        cit_headers = self.get_jwt_header("citizen@test.com", "citizen123")

        # 1. Test public starter questions endpoint for all 3 portals
        for role in ['citizen', 'ngo', 'gov']:
            res = self.client.get(f'/api/public/assistant/starter-questions?role={role}')
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertEqual(data["total"], 5)
            self.assertEqual(len(data["questions"]), 5)

        # 2. Test Citizen Assistant 5 starter questions
        citizen_questions = [
            "How do I send an SOS alert?",
            "Where is the nearest shelter to me?",
            "What should I keep in an emergency go-bag?",
            "How do I track my assigned rescue team?",
            "Who do I call if I can't reach the app?"
        ]
        for q in citizen_questions:
            res = self.client.post('/api/citizen/assistant', json={"message": q}, headers=cit_headers)
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertIn("response", data)
            self.assertIn("Human Verification Required", data["response"])

        # 3. Test NGO Assistant 5 starter questions
        ngo_questions = [
            "How do I form a new rescue squad?",
            "How do I check volunteer availability by skill?",
            "How is SOS priority score calculated?",
            "How do I report a food/shelter deficit?",
            "What equipment is recommended for a flood mission?"
        ]
        for q in ngo_questions:
            res = self.client.post('/api/ngo/ai/assistant', json={"message": q}, headers=ngo_headers)
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertIn("response", data)
            self.assertIn("Human Verification Required", data["response"])

        # 4. Test Government Assistant 5 starter questions & Dynamic DB Lookups
        gov_questions = [
            "Show me all Critical-risk sectors right now.",
            "How do I verify a new NGO?",
            "How do I generate today's situation report PDF?",
            "What triggers a flash-flood warning?",
            "Show unresolved SOS requests older than 30 minutes."
        ]
        for q in gov_questions:
            res = self.client.post('/api/gov/ai/ask', json={"question": q}, headers=gov_headers)
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertIn("response", data)
            self.assertIn("Human Verification Required", data["response"])

    def test_v6_sos_notifications_and_haversine(self):
        cit_headers = self.get_jwt_header("citizen@test.com", "citizen123")
        gov_headers = self.get_jwt_header("admin@gov.in", "admin123")
        ngo_headers = self.get_jwt_header("ngo@test.org", "ngo123")

        # 1. Trigger SOS and verify government and NGO notification persistence
        res = self.client.post('/api/citizen/sos', json={
            "area_id": 1,
            "latitude": 12.9750,
            "longitude": 80.2200,
            "emergency_type": "Flood",
            "people_affected": 4,
            "has_children": True,
            "medical_emergency": True
        }, headers=cit_headers)
        self.assertEqual(res.status_code, 201)

        # Check government notifications
        res_gov_notif = self.client.get('/api/citizen/notifications', headers=gov_headers)
        self.assertEqual(res_gov_notif.status_code, 200)
        gov_notifs = json.loads(res_gov_notif.data)
        self.assertTrue(any("EMERGENCY SOS" in n["title"] or "CRITICAL SOS" in n["title"] for n in gov_notifs))

        # Check NGO notifications
        res_ngo_notif = self.client.get('/api/citizen/notifications', headers=ngo_headers)
        self.assertEqual(res_ngo_notif.status_code, 200)
        ngo_notifs = json.loads(res_ngo_notif.data)
        self.assertTrue(any("EMERGENCY SOS" in n["title"] or "CRITICAL SOS" in n["title"] for n in ngo_notifs))

        # 2. Test Great-circle Haversine formula on /api/citizen/shelters
        res_shelters = self.client.get('/api/citizen/shelters?lat=12.9750&lng=80.2200', headers=cit_headers)
        self.assertEqual(res_shelters.status_code, 200)
        shelters = json.loads(res_shelters.data)
        self.assertGreaterEqual(len(shelters), 1)
        self.assertIn("distance_km", shelters[0])
        self.assertIsInstance(shelters[0]["distance_km"], float)

        # 3. Test Haversine on /api/citizen/hospitals
        res_hosp = self.client.get('/api/citizen/hospitals?lat=12.9750&lng=80.2200', headers=cit_headers)
        self.assertEqual(res_hosp.status_code, 200)
        hospitals = json.loads(res_hosp.data)
        self.assertGreaterEqual(len(hospitals), 1)
        self.assertIn("distance_km", hospitals[0])

    def test_v7_pdf_generation_and_static_serving(self):
        gov_headers = self.get_jwt_header("admin@gov.in", "admin123")

        # 1. Generate ReportLab PDF
        res = self.client.post('/api/gov/reports/generate', json={}, headers=gov_headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn("report_url", data)
        download_url = data["report_url"]

        # 2. Fetch via static reports route
        res_file = self.client.get(download_url)
        self.assertEqual(res_file.status_code, 200)
        self.assertEqual(res_file.mimetype, 'application/pdf')
        self.assertTrue(len(res_file.data) > 500) # Valid non-empty PDF binary

if __name__ == '__main__':
    unittest.main()


