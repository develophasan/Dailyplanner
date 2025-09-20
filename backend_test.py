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
    
    def test_ai_chat_basic(self):
        """Test basic AI chat endpoint functionality"""
        if not self.auth_token:
            self.log_test("AI Chat Basic", False, "No auth token available")
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
                    self.log_test("AI Chat Basic", True, "AI plan generated successfully")
                    return True
                else:
                    self.log_test("AI Chat Basic", False, "Invalid AI response structure")
            else:
                self.log_test("AI Chat Basic", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("AI Chat Basic", False, f"Exception: {str(e)}")
        
        return False

    def test_ai_chat_content_completeness(self):
        """Test AI chat endpoint for complete plan content - CRITICAL TEST"""
        if not self.auth_token:
            self.log_test("AI Chat Content Completeness", False, "No auth token available")
            return False
            
        payload = {
            "message": "60-72 ay yaş grubu için matematik ve sanat etkinlikleri içeren detaylı günlük plan hazırla. Sayı kavramı, geometrik şekiller ve yaratıcı sanat çalışmaları dahil et.",
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("AI Chat Content Completeness", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            print(f"\n🔍 AI Response Analysis:")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Store response for detailed analysis
            self.ai_response = data
            
            # Critical checks for complete plan content
            issues = []
            
            # Check finalize status
            if not data.get("finalize"):
                issues.append("Plan not finalized (finalize: false)")
            
            # Check blocks object exists and is complete
            blocks = data.get("blocks", {})
            if not blocks:
                issues.append("Missing 'blocks' object")
            else:
                # Check activities array
                activities = blocks.get("activities", [])
                if not activities:
                    issues.append("Empty 'blocks.activities' array")
                elif len(activities) == 0:
                    issues.append("'blocks.activities' array has no items")
                else:
                    # Check activity details
                    for i, activity in enumerate(activities):
                        if not activity.get("title"):
                            issues.append(f"Activity {i+1} missing title")
                        if not activity.get("materials"):
                            issues.append(f"Activity {i+1} missing materials")
                        if not activity.get("steps"):
                            issues.append(f"Activity {i+1} missing steps")
                
                # Check assessment array
                assessment = blocks.get("assessment", [])
                if not assessment:
                    issues.append("Empty 'blocks.assessment' array")
                elif len(assessment) == 0:
                    issues.append("'blocks.assessment' array has no items")
            
            # Check domainOutcomes
            domain_outcomes = data.get("domainOutcomes", [])
            if not domain_outcomes:
                issues.append("Empty 'domainOutcomes' array")
            elif len(domain_outcomes) == 0:
                issues.append("'domainOutcomes' array has no items")
            else:
                # Check for proper Turkish educational codes
                valid_codes = False
                for outcome in domain_outcomes:
                    code = outcome.get("code", "")
                    if any(prefix in code for prefix in ["MAB", "TADB", "HSAB", "SNAB", "SDB"]):
                        valid_codes = True
                        break
                if not valid_codes:
                    issues.append("No valid Turkish educational codes in domainOutcomes")
            
            if issues:
                details = f"Content issues found: {'; '.join(issues)}"
                self.log_test("AI Chat Content Completeness", False, details)
                print(f"❌ Issues: {details}")
                return False
            else:
                details = f"Complete plan with {len(activities)} activities, {len(assessment)} assessment methods, {len(domain_outcomes)} domain outcomes"
                self.log_test("AI Chat Content Completeness", True, details)
                print(f"✅ Complete: {details}")
                return True
                
        except Exception as e:
            self.log_test("AI Chat Content Completeness", False, f"Exception: {str(e)}")
        
        return False

    def test_ai_chat_multiple_calls_consistency(self):
        """Test AI chat consistency across multiple calls"""
        if not self.auth_token:
            self.log_test("AI Chat Consistency", False, "No auth token available")
            return False
            
        test_scenarios = [
            {
                "name": "Simple Daily Plan",
                "message": "60-72 ay yaş grubu için basit günlük plan hazırla.",
                "ageBand": "60_72"
            },
            {
                "name": "Math Activities Plan", 
                "message": "60-72 ay yaş grubu için matematik etkinlikleri içeren plan hazırla. Sayma ve şekil tanıma odaklı.",
                "ageBand": "60_72"
            },
            {
                "name": "Art Activities Plan",
                "message": "60-72 ay yaş grubu için sanat etkinlikleri içeren plan hazırla. Boyama ve yaratıcılık odaklı.",
                "ageBand": "60_72"
            }
        ]
        
        consistent_responses = 0
        total_responses = len(test_scenarios)
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            for scenario in test_scenarios:
                payload = {
                    "message": scenario["message"],
                    "history": [],
                    "ageBand": scenario["ageBand"],
                    "planType": "daily"
                }
                
                response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for consistent structure
                    has_required_fields = all(field in data for field in ["finalize", "type", "ageBand", "blocks"])
                    has_activities = bool(data.get("blocks", {}).get("activities"))
                    has_assessment = bool(data.get("blocks", {}).get("assessment"))
                    has_domain_outcomes = bool(data.get("domainOutcomes"))
                    
                    if has_required_fields and has_activities and has_assessment and has_domain_outcomes:
                        consistent_responses += 1
                        print(f"✅ {scenario['name']}: Consistent structure")
                    else:
                        print(f"❌ {scenario['name']}: Inconsistent structure")
                else:
                    print(f"❌ {scenario['name']}: HTTP {response.status_code}")
            
            success_rate = (consistent_responses / total_responses) * 100
            if consistent_responses == total_responses:
                self.log_test("AI Chat Consistency", True, f"All {total_responses} calls returned consistent structure")
                return True
            else:
                self.log_test("AI Chat Consistency", False, f"Only {consistent_responses}/{total_responses} calls consistent ({success_rate:.1f}%)")
                return False
                
        except Exception as e:
            self.log_test("AI Chat Consistency", False, f"Exception: {str(e)}")
        
        return False

    def test_ai_chat_incomplete_info_handling(self):
        """Test AI chat with incomplete information - should ask follow-up questions"""
        if not self.auth_token:
            self.log_test("AI Chat Incomplete Info", False, "No auth token available")
            return False
            
        payload = {
            "message": "Plan hazırla.",  # Very vague request
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should either ask follow-up questions or provide a basic plan
                has_follow_up = bool(data.get("followUpQuestions"))
                has_missing_fields = bool(data.get("missingFields"))
                is_finalized = data.get("finalize", False)
                
                if has_follow_up or has_missing_fields or not is_finalized:
                    self.log_test("AI Chat Incomplete Info", True, "AI properly handles incomplete information")
                    return True
                else:
                    # If finalized, should still have complete content
                    blocks = data.get("blocks", {})
                    has_activities = bool(blocks.get("activities"))
                    has_assessment = bool(blocks.get("assessment"))
                    
                    if has_activities and has_assessment:
                        self.log_test("AI Chat Incomplete Info", True, "AI provided complete plan despite vague request")
                        return True
                    else:
                        self.log_test("AI Chat Incomplete Info", False, "AI finalized incomplete plan")
                        return False
            else:
                self.log_test("AI Chat Incomplete Info", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("AI Chat Incomplete Info", False, f"Exception: {str(e)}")
        
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