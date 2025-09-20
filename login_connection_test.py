#!/usr/bin/env python3
"""
MaarifPlanner Login Connection Test - As requested in review
Tests auth endpoints, login flow, connection, and database integration
"""

import requests
import json
import time
import sys
from datetime import datetime

# Test Configuration - Using localhost as specified in review
BACKEND_URL = "http://localhost:8001"
API_BASE = f"{BACKEND_URL}/api"

# Test Data - Using realistic Turkish educational data as requested
TEST_USER = {
    "email": "test@example.com",
    "password": "testpass123",
    "name": "Test Öğretmen",
    "school": "Test Anaokulu",
    "className": "Test Sınıfı",
    "ageDefault": "60_72"
}

def test_backend_connection():
    """Test if backend service is running"""
    print("🔍 Testing Backend Connection...")
    try:
        start_time = time.time()
        response = requests.get(f"{BACKEND_URL}/docs", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ Backend Service Connection: OK ({response_time:.2f}s)")
            return True
        else:
            print(f"❌ Backend Service Connection: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Backend Service Connection: Cannot connect to {BACKEND_URL}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Backend Service Connection: Timeout")
        return False
    except Exception as e:
        print(f"❌ Backend Service Connection: Error - {str(e)}")
        return False

def test_cors_headers():
    """Test CORS configuration"""
    print("\n🌐 Testing CORS Configuration...")
    try:
        start_time = time.time()
        response = requests.options(f"{API_BASE}/auth/login", 
                                  headers={
                                      "Origin": "http://localhost:3000",
                                      "Access-Control-Request-Method": "POST",
                                      "Access-Control-Request-Headers": "Content-Type"
                                  }, timeout=10)
        response_time = time.time() - start_time
        
        cors_origin = response.headers.get("Access-Control-Allow-Origin")
        cors_methods = response.headers.get("Access-Control-Allow-Methods")
        
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Allow-Origin: {cors_origin}")
        print(f"   Allow-Methods: {cors_methods}")
        
        if cors_origin:
            print("✅ CORS Headers: Configured")
            return True
        else:
            print("❌ CORS Headers: Missing or misconfigured")
            return False
            
    except Exception as e:
        print(f"❌ CORS Headers: Error - {str(e)}")
        return False

def test_auth_register():
    """Test /api/auth/register endpoint"""
    print(f"\n👤 Testing Auth Register Endpoint...")
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE}/auth/register", 
                               json=TEST_USER, 
                               timeout=10)
        response_time = time.time() - start_time
        
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                print(f"   User Created: {data['user']['name']} ({data['user']['email']})")
                print("✅ Auth Register: SUCCESS")
                return data["token"], data["user"]["id"]
            else:
                print(f"   Response: {data}")
                print("❌ Auth Register: Invalid response format")
                return None, None
        elif response.status_code == 400:
            error_data = response.json()
            if "already registered" in error_data.get("detail", ""):
                print("   User already exists - proceeding with login test")
                print("✅ Auth Register: User exists (expected)")
                return None, None
            else:
                print(f"   Error: {error_data}")
                print("❌ Auth Register: Registration failed")
                return None, None
        else:
            print(f"   Error: {response.text}")
            print(f"❌ Auth Register: HTTP {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"❌ Auth Register: Exception - {str(e)}")
        return None, None

def test_auth_login():
    """Test /api/auth/login endpoint"""
    print(f"\n🔐 Testing Auth Login Endpoint...")
    try:
        start_time = time.time()
        login_data = {
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
        response = requests.post(f"{API_BASE}/auth/login", 
                               json=login_data, 
                               timeout=10)
        response_time = time.time() - start_time
        
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                print(f"   Login Success: {data['user']['name']} ({data['user']['email']})")
                print("✅ Auth Login: SUCCESS")
                return data["token"], data["user"]["id"]
            else:
                print(f"   Response: {data}")
                print("❌ Auth Login: Invalid response format")
                return None, None
        elif response.status_code == 401:
            print("   Invalid credentials")
            print("❌ Auth Login: Authentication failed")
            return None, None
        else:
            print(f"   Error: {response.text}")
            print(f"❌ Auth Login: HTTP {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"❌ Auth Login: Exception - {str(e)}")
        return None, None

def test_invalid_login():
    """Test login with invalid credentials"""
    print(f"\n🚫 Testing Invalid Login Credentials...")
    try:
        start_time = time.time()
        invalid_data = {
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        }
        response = requests.post(f"{API_BASE}/auth/login", 
                               json=invalid_data, 
                               timeout=10)
        response_time = time.time() - start_time
        
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("   Invalid credentials properly rejected")
            print("✅ Invalid Login Test: SUCCESS")
            return True
        else:
            print(f"   Expected 401, got {response.status_code}")
            print("❌ Invalid Login Test: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Invalid Login Test: Exception - {str(e)}")
        return False

def test_auth_me(token):
    """Test /api/auth/me endpoint"""
    print(f"\n🔍 Testing Token Validation (/auth/me)...")
    if not token:
        print("❌ Token Validation: No token available")
        return False
        
    try:
        start_time = time.time()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE}/auth/me", 
                              headers=headers, 
                              timeout=10)
        response_time = time.time() - start_time
        
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data and "email" in data and "name" in data:
                print(f"   User Info: {data['name']} ({data['email']})")
                print("✅ Token Validation: SUCCESS")
                return True
            else:
                print(f"   Response: {data}")
                print("❌ Token Validation: Invalid response format")
                return False
        elif response.status_code == 401:
            print("   Token validation failed")
            print("❌ Token Validation: Invalid token")
            return False
        else:
            print(f"   Error: {response.text}")
            print(f"❌ Token Validation: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Token Validation: Exception - {str(e)}")
        return False

def test_database_integration(token):
    """Test database operations through API"""
    print(f"\n🗄️ Testing Database Integration...")
    if not token:
        print("❌ Database Integration: No token available")
        return False
        
    try:
        # Test creating a daily plan
        start_time = time.time()
        plan_data = {
            "date": "2024-01-15",
            "ageBand": "60_72",
            "title": "Test Günlük Planı",
            "planJson": {
                "theme": "Test Teması",
                "activities": ["Test Etkinliği 1", "Test Etkinliği 2"],
                "ageBand": "60_72",
                "date": "2024-01-15"
            }
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{API_BASE}/plans/daily", 
                               json=plan_data, 
                               headers=headers, 
                               timeout=10)
        response_time = time.time() - start_time
        
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            plan_id = data.get("id")
            print(f"   Plan Created: ID {plan_id}")
            
            # Test retrieving the plan
            get_response = requests.get(f"{API_BASE}/plans/daily/{plan_id}", 
                                      headers=headers, 
                                      timeout=10)
            
            if get_response.status_code == 200:
                plan_data = get_response.json()
                print(f"   Plan Retrieved: {plan_data.get('title', 'Untitled')}")
                print("✅ Database Integration: SUCCESS")
                return True
            else:
                print(f"   Failed to retrieve plan: {get_response.status_code}")
                print("❌ Database Integration: Retrieval failed")
                return False
        else:
            print(f"   Error: {response.text}")
            print(f"❌ Database Integration: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Database Integration: Exception - {str(e)}")
        return False

def main():
    """Main test execution"""
    print("🚀 MaarifPlanner Login Connection Test")
    print("=" * 50)
    print("Testing as requested in review:")
    print("- Auth endpoints (/api/auth/register, /api/auth/login, /api/auth/me)")
    print("- Login flow with test@example.com / testpass123")
    print("- Connection and CORS testing")
    print("- Database integration")
    print("=" * 50)
    
    results = []
    
    # Test 1: Backend Connection
    results.append(("Backend Connection", test_backend_connection()))
    
    # Test 2: CORS Configuration
    results.append(("CORS Configuration", test_cors_headers()))
    
    # Test 3: User Registration
    token, user_id = test_auth_register()
    results.append(("Auth Register", token is not None or user_id is not None))
    
    # Test 4: User Login
    if not token:  # If registration didn't return token, try login
        token, user_id = test_auth_login()
    results.append(("Auth Login", token is not None))
    
    # Test 5: Invalid Login
    results.append(("Invalid Login Rejection", test_invalid_login()))
    
    # Test 6: Token Validation
    results.append(("Token Validation", test_auth_me(token)))
    
    # Test 7: Database Integration
    results.append(("Database Integration", test_database_integration(token)))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All login connection tests PASSED!")
        return True
    else:
        print(f"\n⚠️ {total-passed} test(s) FAILED - Check connection issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)