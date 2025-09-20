#!/usr/bin/env python3
"""
MaarifPlanner Backend Edge Case Tests
Tests error handling, validation, and edge cases
"""

import requests
import json
import uuid

BACKEND_URL = "https://plan-tester-1.preview.emergentagent.com/api"

class EdgeCaseTester:
    def __init__(self):
        self.base_url = BACKEND_URL
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
    
    def test_invalid_registration(self):
        """Test registration with invalid data"""
        # Missing required fields
        payload = {
            "email": "incomplete@test.com"
            # Missing password and name
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/register", json=payload)
            if response.status_code == 422:  # Validation error expected
                self.log_test("Invalid Registration (Missing Fields)", True, "Correctly rejected incomplete data")
                return True
            else:
                self.log_test("Invalid Registration (Missing Fields)", False, f"Expected 422, got {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Registration (Missing Fields)", False, f"Exception: {str(e)}")
        
        return False
    
    def test_duplicate_email_registration(self):
        """Test registration with duplicate email"""
        test_email = f"duplicate_{uuid.uuid4().hex[:8]}@test.com"
        
        # First registration
        payload = {
            "email": test_email,
            "password": "TestPass123!",
            "name": "Test User"
        }
        
        try:
            # Register first user
            response1 = requests.post(f"{self.base_url}/auth/register", json=payload)
            if response1.status_code != 200:
                self.log_test("Duplicate Email Registration", False, "Failed to create first user")
                return False
            
            # Try to register same email again
            response2 = requests.post(f"{self.base_url}/auth/register", json=payload)
            if response2.status_code == 400:  # Conflict expected
                self.log_test("Duplicate Email Registration", True, "Correctly rejected duplicate email")
                return True
            else:
                self.log_test("Duplicate Email Registration", False, f"Expected 400, got {response2.status_code}")
        except Exception as e:
            self.log_test("Duplicate Email Registration", False, f"Exception: {str(e)}")
        
        return False
    
    def test_invalid_login(self):
        """Test login with wrong credentials"""
        payload = {
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=payload)
            if response.status_code == 401:  # Unauthorized expected
                self.log_test("Invalid Login", True, "Correctly rejected invalid credentials")
                return True
            else:
                self.log_test("Invalid Login", False, f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Login", False, f"Exception: {str(e)}")
        
        return False
    
    def test_unauthorized_access(self):
        """Test accessing protected endpoints without token"""
        try:
            response = requests.get(f"{self.base_url}/auth/me")
            if response.status_code == 403:  # Forbidden expected
                self.log_test("Unauthorized Access", True, "Correctly rejected request without token")
                return True
            else:
                self.log_test("Unauthorized Access", False, f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_test("Unauthorized Access", False, f"Exception: {str(e)}")
        
        return False
    
    def test_invalid_token(self):
        """Test accessing protected endpoints with invalid token"""
        try:
            headers = {"Authorization": "Bearer invalid_token_here"}
            response = requests.get(f"{self.base_url}/auth/me", headers=headers)
            if response.status_code == 401:  # Unauthorized expected
                self.log_test("Invalid Token", True, "Correctly rejected invalid token")
                return True
            else:
                self.log_test("Invalid Token", False, f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Token", False, f"Exception: {str(e)}")
        
        return False
    
    def test_invalid_plan_data(self):
        """Test creating plan with invalid data"""
        # First get a valid token
        test_email = f"plantest_{uuid.uuid4().hex[:8]}@test.com"
        register_payload = {
            "email": test_email,
            "password": "TestPass123!",
            "name": "Plan Test User"
        }
        
        try:
            reg_response = requests.post(f"{self.base_url}/auth/register", json=register_payload)
            if reg_response.status_code != 200:
                self.log_test("Invalid Plan Data", False, "Failed to create test user")
                return False
            
            token = reg_response.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Try to create plan with invalid date format
            invalid_payload = {
                "date": "invalid-date-format",
                "ageBand": "60_72",
                "planJson": {}
            }
            
            response = requests.post(f"{self.base_url}/plans/daily", json=invalid_payload, headers=headers)
            if response.status_code in [400, 422]:  # Bad request or validation error expected
                self.log_test("Invalid Plan Data", True, "Correctly rejected invalid plan data")
                return True
            else:
                self.log_test("Invalid Plan Data", False, f"Expected 400/422, got {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Plan Data", False, f"Exception: {str(e)}")
        
        return False
    
    def test_nonexistent_plan_access(self):
        """Test accessing non-existent plan"""
        # First get a valid token
        test_email = f"planaccess_{uuid.uuid4().hex[:8]}@test.com"
        register_payload = {
            "email": test_email,
            "password": "TestPass123!",
            "name": "Plan Access Test User"
        }
        
        try:
            reg_response = requests.post(f"{self.base_url}/auth/register", json=register_payload)
            if reg_response.status_code != 200:
                self.log_test("Nonexistent Plan Access", False, "Failed to create test user")
                return False
            
            token = reg_response.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Try to access non-existent plan
            fake_plan_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
            response = requests.get(f"{self.base_url}/plans/daily/{fake_plan_id}", headers=headers)
            
            if response.status_code == 404:  # Not found expected
                self.log_test("Nonexistent Plan Access", True, "Correctly returned 404 for non-existent plan")
                return True
            else:
                self.log_test("Nonexistent Plan Access", False, f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_test("Nonexistent Plan Access", False, f"Exception: {str(e)}")
        
        return False
    
    def run_all_tests(self):
        """Run all edge case tests"""
        print("🔍 Starting MaarifPlanner Backend Edge Case Tests")
        print("=" * 50)
        
        self.test_invalid_registration()
        self.test_duplicate_email_registration()
        self.test_invalid_login()
        self.test_unauthorized_access()
        self.test_invalid_token()
        self.test_invalid_plan_data()
        self.test_nonexistent_plan_access()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 EDGE CASE TEST SUMMARY:")
        
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
    tester = EdgeCaseTester()
    passed, total = tester.run_all_tests()