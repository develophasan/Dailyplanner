#!/usr/bin/env python3
"""
Focused AI Chat API Test for Review Request
Tests the specific request: "60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur"
"""

import requests
import json
import uuid
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://plan-tester-1.preview.emergentagent.com/api"

def test_ai_chat_review_request():
    """Test the exact AI Chat request from the review"""
    print("🚀 Testing AI Chat API as per Review Request")
    print("=" * 60)
    
    # Step 1: Register a test user
    print("\n1️⃣ Registering test user...")
    test_email = f"test_{uuid.uuid4().hex[:8]}@maarif.edu.tr"
    register_payload = {
        "email": test_email,
        "password": "TestPass123!",
        "name": "Test Öğretmen",
        "school": "Test Okulu",
        "className": "Test Sınıfı",
        "ageDefault": "60_72"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/auth/register", json=register_payload)
        if response.status_code != 200:
            print(f"❌ Registration failed: HTTP {response.status_code}: {response.text}")
            return False
        
        data = response.json()
        auth_token = data["token"]
        print(f"✅ User registered successfully: {data['user']['name']}")
        
    except Exception as e:
        print(f"❌ Registration exception: {str(e)}")
        return False
    
    # Step 2: Test the exact AI Chat request from review
    print("\n2️⃣ Testing AI Chat with exact review request...")
    print("Request: '60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur'")
    
    payload = {
        "message": "60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur",
        "history": [],
        "ageBand": "60_72",
        "planType": "daily"
    }
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BACKEND_URL}/ai/chat", json=payload, headers=headers)
        
        print(f"Response Status: HTTP {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ AI Chat API failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
            # Check if it's authentication error
            if "authentication" in response.text.lower() or "api key" in response.text.lower():
                print("🔍 AUTHENTICATION ERROR DETECTED - API key issue")
            
            return False
        
        # Parse and analyze the response
        data = response.json()
        print("✅ AI Chat API responded successfully")
        
        # Step 3: Analyze plan quality as per review criteria
        print("\n3️⃣ Analyzing plan quality as per review criteria...")
        
        # Check if plan is finalized
        finalized = data.get("finalize", False)
        print(f"Plan finalized: {finalized}")
        
        # Check blocks structure
        blocks = data.get("blocks", {})
        if not blocks:
            print("❌ Missing 'blocks' structure")
            return False
        
        # Check activities (should contain 8-12 materials and 8-12 steps)
        activities = blocks.get("activities", [])
        print(f"\n📋 Activities Analysis ({len(activities)} activities found):")
        
        for i, activity in enumerate(activities):
            title = activity.get("title", "Untitled")
            materials = activity.get("materials", [])
            steps = activity.get("steps", [])
            
            print(f"   Activity {i+1}: {title}")
            print(f"   - Materials: {len(materials)} items")
            print(f"   - Steps: {len(steps)} items")
            
            # Review criteria: 8-12 materials
            if len(materials) < 8 or len(materials) > 12:
                print(f"   ⚠️  Materials count ({len(materials)}) not in optimal range (8-12)")
            else:
                print(f"   ✅ Materials count optimal")
            
            # Review criteria: 8-12 steps
            if len(steps) < 8 or len(steps) > 12:
                print(f"   ⚠️  Steps count ({len(steps)}) not in optimal range (8-12)")
            else:
                print(f"   ✅ Steps count optimal")
        
        # Check area codes (should be realistic like TAEOB1, SNAB4, MHB4)
        domain_outcomes = data.get("domainOutcomes", [])
        print(f"\n🎯 Domain Outcomes Analysis ({len(domain_outcomes)} domains found):")
        
        realistic_codes = []
        for outcome in domain_outcomes:
            code = outcome.get("code", "")
            print(f"   - {code}")
            
            # Check for realistic Turkish educational codes
            if any(prefix in code for prefix in ["TAEOB", "SNAB", "MHB", "MAB", "HSAB", "SDB"]):
                realistic_codes.append(code)
        
        print(f"   ✅ Realistic area codes found: {len(realistic_codes)}/{len(domain_outcomes)}")
        
        # Check assessment methods (should be 5-7 methods)
        assessment = blocks.get("assessment", [])
        print(f"\n📊 Assessment Methods Analysis ({len(assessment)} methods found):")
        
        for method in assessment:
            print(f"   - {method}")
        
        if len(assessment) >= 5 and len(assessment) <= 7:
            print(f"   ✅ Assessment methods count optimal (5-7)")
        else:
            print(f"   ⚠️  Assessment methods count ({len(assessment)}) not in optimal range (5-7)")
        
        # Check differentiation strategies
        differentiation = data.get("differentiation", {})
        print(f"\n🎨 Differentiation Strategies:")
        if differentiation:
            print(f"   ✅ Differentiation strategies included")
            for key, value in differentiation.items():
                print(f"   - {key}: {value}")
        else:
            print(f"   ⚠️  No differentiation strategies found")
        
        # Check family/community involvement
        family_involvement = data.get("familyCommunityInvolvement", "")
        print(f"\n👨‍👩‍👧‍👦 Family/Community Involvement:")
        if family_involvement:
            print(f"   ✅ Family involvement suggestions included")
            print(f"   - {family_involvement}")
        else:
            print(f"   ⚠️  No family involvement suggestions found")
        
        # Overall quality assessment
        print(f"\n📈 OVERALL PLAN QUALITY ASSESSMENT:")
        quality_score = 0
        total_criteria = 6
        
        if finalized:
            quality_score += 1
            print("   ✅ Plan is finalized")
        else:
            print("   ❌ Plan is not finalized")
        
        if len(activities) >= 3:
            quality_score += 1
            print("   ✅ Sufficient activities (3+)")
        else:
            print("   ❌ Insufficient activities")
        
        if len(realistic_codes) >= 3:
            quality_score += 1
            print("   ✅ Realistic area codes")
        else:
            print("   ❌ Insufficient realistic area codes")
        
        if len(assessment) >= 5:
            quality_score += 1
            print("   ✅ Comprehensive assessment methods")
        else:
            print("   ❌ Insufficient assessment methods")
        
        if differentiation:
            quality_score += 1
            print("   ✅ Differentiation strategies included")
        else:
            print("   ❌ No differentiation strategies")
        
        if family_involvement:
            quality_score += 1
            print("   ✅ Family involvement included")
        else:
            print("   ❌ No family involvement")
        
        print(f"\n🏆 QUALITY SCORE: {quality_score}/{total_criteria} ({(quality_score/total_criteria)*100:.1f}%)")
        
        if quality_score >= 5:
            print("✅ HIGH QUALITY PLAN - Meets review criteria")
            return True
        elif quality_score >= 3:
            print("⚠️  MODERATE QUALITY PLAN - Some improvements needed")
            return True
        else:
            print("❌ LOW QUALITY PLAN - Significant improvements needed")
            return False
        
    except Exception as e:
        print(f"❌ AI Chat test exception: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_ai_chat_review_request()
    print(f"\n{'='*60}")
    if success:
        print("🎉 AI CHAT TEST COMPLETED SUCCESSFULLY")
    else:
        print("💥 AI CHAT TEST FAILED")
    print(f"{'='*60}")