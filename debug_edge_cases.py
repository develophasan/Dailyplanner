#!/usr/bin/env python3
"""
Debug the edge case failures
"""

import requests
import json
import uuid

BACKEND_URL = "https://plan-tester-1.preview.emergentagent.com/api"

def test_invalid_token_debug():
    """Debug the invalid token test"""
    print("🔍 Testing invalid token...")
    try:
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = requests.get(f"{BACKEND_URL}/auth/me", headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

def test_invalid_plan_data_debug():
    """Debug the invalid plan data test"""
    print("\n🔍 Testing invalid plan data...")
    
    # First get a valid token
    test_email = f"debug_{uuid.uuid4().hex[:8]}@test.com"
    register_payload = {
        "email": test_email,
        "password": "TestPass123!",
        "name": "Debug User"
    }
    
    try:
        reg_response = requests.post(f"{BACKEND_URL}/auth/register", json=register_payload)
        if reg_response.status_code != 200:
            print("Failed to create test user")
            return
        
        token = reg_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to create plan with invalid date format
        invalid_payload = {
            "date": "invalid-date-format",
            "ageBand": "60_72",
            "planJson": {}
        }
        
        response = requests.post(f"{BACKEND_URL}/plans/daily", json=invalid_payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    test_invalid_token_debug()
    test_invalid_plan_data_debug()