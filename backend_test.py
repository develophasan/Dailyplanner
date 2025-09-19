#!/usr/bin/env python3
"""
MaarifPlanner Backend API Test Suite
Tests all backend endpoints with realistic Turkish educational data
"""

import requests
import json
import sys
from datetime import datetime, timedelta
import uuid

# Backend URL from environment
BACKEND_URL = "https://dailyplanner-8.preview.emergentagent.com/api"

class MaarifPlannerTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_id = None
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def test_auth_register(self):
        """Test user registration"""
        test_email = f"ogretmen_{uuid.uuid4().hex[:8]}@maarif.edu.tr"
        payload = {
            "email": test_email,
            "password": "MaarifPlan2024!",
            "name": "Ayşe Öğretmen",
            "school": "Atatürk İlkokulu",
            "className": "Papatya Sınıfı",
            "ageDefault": "60_72"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/register", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "user" in data:
                    self.auth_token = data["token"]
                    self.user_id = data["user"]["id"]
                    self.log_test("Auth Registration", True, f"User created: {data['user']['name']}")
                    return True
                else:
                    self.log_test("Auth Registration", False, "Missing token or user in response")
            else:
                self.log_test("Auth Registration", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Auth Registration", False, f"Exception: {str(e)}")
        
        return False
    
    def test_auth_login(self):
        """Test user login with existing credentials"""
        # First register a user for login test
        test_email = f"login_test_{uuid.uuid4().hex[:8]}@maarif.edu.tr"
        register_payload = {
            "email": test_email,
            "password": "TestLogin123!",
            "name": "Mehmet Öğretmen",
            "school": "Cumhuriyet Anaokulu"
        }
        
        try:
            # Register user first
            reg_response = requests.post(f"{self.base_url}/auth/register", json=register_payload)
            if reg_response.status_code != 200:
                self.log_test("Auth Login", False, "Failed to create test user for login")
                return False
            
            # Now test login
            login_payload = {
                "email": test_email,
                "password": "TestLogin123!"
            }
            
            response = requests.post(f"{self.base_url}/auth/login", json=login_payload)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "user" in data:
                    self.log_test("Auth Login", True, f"Login successful for: {data['user']['name']}")
                    return True
                else:
                    self.log_test("Auth Login", False, "Missing token or user in response")
            else:
                self.log_test("Auth Login", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Auth Login", False, f"Exception: {str(e)}")
        
        return False
    
    def test_auth_me(self):
        """Test getting current user info"""
        if not self.auth_token:
            self.log_test("Auth Me", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "email" in data and "name" in data:
                    self.log_test("Auth Me", True, f"User info retrieved: {data['name']}")
                    return True
                else:
                    self.log_test("Auth Me", False, "Missing required user fields")
            else:
                self.log_test("Auth Me", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Auth Me", False, f"Exception: {str(e)}")
        
        return False
    
    def test_ai_chat(self):
        """Test AI chat endpoint with plan generation"""
        if not self.auth_token:
            self.log_test("AI Chat", False, "No auth token available")
            return False
            
        payload = {
            "message": "60-72 ay yaş grubu için matematik etkinlikleri içeren günlük plan hazırla. Sayı kavramı ve geometrik şekiller üzerine odaklan.",
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Check if response has expected AI plan structure
                if isinstance(data, dict) and ("finalize" in data or "type" in data or "blocks" in data):
                    self.log_test("AI Chat", True, "AI plan generated successfully")
                    return True
                else:
                    self.log_test("AI Chat", False, "Invalid AI response structure")
            else:
                self.log_test("AI Chat", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("AI Chat", False, f"Exception: {str(e)}")
        
        return False
    
    def test_daily_plans_create(self):
        """Test creating a daily plan"""
        if not self.auth_token:
            self.log_test("Daily Plans Create", False, "No auth token available")
            return False
            
        today = datetime.now().strftime("%Y-%m-%d")
        payload = {
            "date": today,
            "ageBand": "60_72",
            "title": "Matematik ve Sanat Günlük Planı",
            "planJson": {
                "type": "daily",
                "ageBand": "60_72",
                "date": today,
                "finalize": True,
                "domainOutcomes": [
                    {
                        "code": "MAB.1",
                        "indicators": ["Sayıları tanır", "1-10 arası sayar"],
                        "notes": "Somut materyallerle desteklenir"
                    }
                ],
                "blocks": {
                    "startOfDay": "Günaydın şarkısı ve yoklama",
                    "activities": [
                        {
                            "title": "Sayı Bahçesi",
                            "location": "Matematik merkezi",
                            "materials": ["Renkli sayı kartları", "Doğal materyaller"],
                            "steps": ["Sayıları tanıma", "Eşleştirme oyunu", "Sıralama"]
                        }
                    ],
                    "assessment": ["Gözlem formu", "Fotoğraf"]
                }
            }
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/plans/daily", json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "message" in data:
                    self.plan_id = data["id"]
                    self.log_test("Daily Plans Create", True, f"Plan created with ID: {data['id']}")
                    return True
                else:
                    self.log_test("Daily Plans Create", False, "Missing id or message in response")
            else:
                self.log_test("Daily Plans Create", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Daily Plans Create", False, f"Exception: {str(e)}")
        
        return False
    
    def test_daily_plans_list(self):
        """Test getting list of daily plans"""
        if not self.auth_token:
            self.log_test("Daily Plans List", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/plans/daily", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Daily Plans List", True, f"Retrieved {len(data)} plans")
                    return True
                else:
                    self.log_test("Daily Plans List", False, "Response is not a list")
            else:
                self.log_test("Daily Plans List", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Daily Plans List", False, f"Exception: {str(e)}")
        
        return False
    
    def test_daily_plans_get_by_id(self):
        """Test getting a specific daily plan by ID"""
        if not self.auth_token:
            self.log_test("Daily Plans Get by ID", False, "No auth token available")
            return False
            
        if not hasattr(self, 'plan_id'):
            self.log_test("Daily Plans Get by ID", False, "No plan ID available from create test")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/plans/daily/{self.plan_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "planJson" in data and "date" in data:
                    self.log_test("Daily Plans Get by ID", True, f"Plan retrieved: {data.get('title', 'Untitled')}")
                    return True
                else:
                    self.log_test("Daily Plans Get by ID", False, "Missing required fields in plan")
            else:
                self.log_test("Daily Plans Get by ID", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Daily Plans Get by ID", False, f"Exception: {str(e)}")
        
        return False
    
    def test_monthly_plans_create(self):
        """Test creating a monthly plan"""
        if not self.auth_token:
            self.log_test("Monthly Plans Create", False, "No auth token available")
            return False
            
        current_month = datetime.now().strftime("%Y-%m")
        payload = {
            "month": current_month,
            "ageBand": "60_72",
            "title": f"Aylık Plan - {current_month}",
            "planJson": {
                "type": "monthly",
                "ageBand": "60_72",
                "month": current_month,
                "themes": ["Doğa ve Çevre", "Matematik Kavramları"],
                "weeklyGoals": [
                    "Hafta 1: Mevsim değişikliklerini gözlemle",
                    "Hafta 2: Sayıları tanı ve say",
                    "Hafta 3: Geometrik şekilleri keşfet",
                    "Hafta 4: Doğal materyallerle sanat"
                ]
            }
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/plans/monthly", json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "message" in data:
                    self.log_test("Monthly Plans Create", True, f"Monthly plan created with ID: {data['id']}")
                    return True
                else:
                    self.log_test("Monthly Plans Create", False, "Missing id or message in response")
            else:
                self.log_test("Monthly Plans Create", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Monthly Plans Create", False, f"Exception: {str(e)}")
        
        return False
    
    def test_monthly_plans_list(self):
        """Test getting list of monthly plans"""
        if not self.auth_token:
            self.log_test("Monthly Plans List", False, "No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/plans/monthly", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Monthly Plans List", True, f"Retrieved {len(data)} monthly plans")
                    return True
                else:
                    self.log_test("Monthly Plans List", False, "Response is not a list")
            else:
                self.log_test("Monthly Plans List", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Monthly Plans List", False, f"Exception: {str(e)}")
        
        return False
    
    def test_matrix_search(self):
        """Test matrix search functionality"""
        try:
            # Test basic search
            response = requests.get(f"{self.base_url}/matrix/search?q=MAB&ageBand=60_72")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Matrix Search", True, f"Search returned {len(data)} results")
                    return True
                else:
                    self.log_test("Matrix Search", False, "Response is not a list")
            else:
                self.log_test("Matrix Search", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Matrix Search", False, f"Exception: {str(e)}")
        
        return False
    
    def run_all_tests(self):
        """Run all backend tests in order"""
        print("🚀 Starting MaarifPlanner Backend API Tests")
        print("=" * 50)
        
        # High Priority Tests
        print("\n📋 HIGH PRIORITY TESTS:")
        self.test_auth_register()
        self.test_auth_login()
        self.test_auth_me()
        self.test_ai_chat()
        self.test_daily_plans_create()
        self.test_daily_plans_list()
        self.test_daily_plans_get_by_id()
        
        # Medium Priority Tests
        print("\n📋 MEDIUM PRIORITY TESTS:")
        self.test_monthly_plans_create()
        self.test_monthly_plans_list()
        self.test_matrix_search()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY:")
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if total - passed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   ❌ {result['test']}: {result['details']}")
        
        return passed, total

if __name__ == "__main__":
    tester = MaarifPlannerTester()
    passed, total = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    sys.exit(0 if passed == total else 1)