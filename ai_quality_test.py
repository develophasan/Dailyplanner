#!/usr/bin/env python3
"""
MaarifPlanner AI System Prompt Quality Test
Specific test for the review request to validate AI plan generation quality
"""

import requests
import json
import sys
from datetime import datetime
import uuid

# Backend URL from app.json
BACKEND_URL = "https://plan-tester-1.preview.emergentagent.com/api"

class AIQualityTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_id = None
        
    def setup_auth(self):
        """Setup authentication for testing"""
        test_email = f"ai_test_{uuid.uuid4().hex[:8]}@maarif.edu.tr"
        payload = {
            "email": test_email,
            "password": "AITest2024!",
            "name": "AI Test Öğretmeni",
            "school": "Test Anaokulu",
            "className": "Test Sınıfı",
            "ageDefault": "60_72"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/register", json=payload)
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.user_id = data["user"]["id"]
                print(f"✅ Authentication setup successful")
                return True
            else:
                print(f"❌ Auth setup failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Auth setup exception: {str(e)}")
            return False
    
    def test_ai_plan_quality_review_request(self):
        """
        MAIN TEST: Test AI Chat API for updated system prompt quality
        As requested in review: "60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur"
        """
        if not self.auth_token:
            print("❌ No auth token available")
            return False
            
        # Exact request as specified in review
        payload = {
            "message": "60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur",
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            print(f"\n🎯 TESTING AI CHAT API WITH REVIEW REQUEST:")
            print(f"Request: {payload['message']}")
            print(f"Age Band: {payload['ageBand']}")
            
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ API Request Failed: HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            print(f"✅ AI API Response received successfully")
            
            # Store response for detailed analysis
            self.ai_response = data
            
            # DETAILED QUALITY ANALYSIS AS PER REVIEW CRITERIA
            print(f"\n📋 DETAILED PLAN QUALITY ANALYSIS:")
            print(f"=" * 60)
            
            issues = []
            warnings = []
            quality_score = 0
            max_score = 7  # 7 criteria from review
            
            # 1. CHECK: Activities should have 8-12 materials
            print(f"\n1️⃣ MATERIALS ANALYSIS (Review Requirement: 8-12 per activity):")
            blocks = data.get("blocks", {})
            activities = blocks.get("activities", [])
            
            if not activities:
                issues.append("No activities found in plan")
                print(f"   ❌ No activities found")
            else:
                materials_compliant = 0
                for i, activity in enumerate(activities):
                    materials = activity.get("materials", [])
                    material_count = len(materials)
                    
                    if 8 <= material_count <= 12:
                        print(f"   ✅ Activity {i+1}: {material_count} materials (compliant)")
                        materials_compliant += 1
                    else:
                        print(f"   ⚠️ Activity {i+1}: {material_count} materials (should be 8-12)")
                        warnings.append(f"Activity {i+1} has {material_count} materials (should be 8-12)")
                
                if materials_compliant == len(activities):
                    quality_score += 1
                    print(f"   🎯 MATERIALS CRITERION: PASSED ({materials_compliant}/{len(activities)} activities compliant)")
                else:
                    print(f"   ❌ MATERIALS CRITERION: FAILED ({materials_compliant}/{len(activities)} activities compliant)")
            
            # 2. CHECK: Each activity should have 8-12 detailed steps
            print(f"\n2️⃣ STEPS ANALYSIS (Review Requirement: 8-12 per activity):")
            if activities:
                steps_compliant = 0
                for i, activity in enumerate(activities):
                    steps = activity.get("steps", [])
                    steps_count = len(steps)
                    
                    if 8 <= steps_count <= 12:
                        print(f"   ✅ Activity {i+1}: {steps_count} steps (compliant)")
                        steps_compliant += 1
                    else:
                        print(f"   ⚠️ Activity {i+1}: {steps_count} steps (should be 8-12)")
                        warnings.append(f"Activity {i+1} has {steps_count} steps (should be 8-12)")
                
                if steps_compliant == len(activities):
                    quality_score += 1
                    print(f"   🎯 STEPS CRITERION: PASSED ({steps_compliant}/{len(activities)} activities compliant)")
                else:
                    print(f"   ❌ STEPS CRITERION: FAILED ({steps_compliant}/{len(activities)} activities compliant)")
            
            # 3. CHECK: Domain codes should be realistic (TAEOB1, SNAB4, MHB4, etc.)
            print(f"\n3️⃣ DOMAIN CODES ANALYSIS (Review Requirement: Realistic codes like TAEOB1, SNAB4, MHB4):")
            domain_outcomes = data.get("domainOutcomes", [])
            
            if not domain_outcomes:
                issues.append("No domain outcomes found")
                print(f"   ❌ No domain outcomes found")
            else:
                valid_prefixes = ["TAEOB", "SNAB", "MHB", "MAB", "HSAB", "SDB", "TADB"]
                valid_codes = 0
                
                for outcome in domain_outcomes:
                    code = outcome.get("code", "")
                    is_valid = any(code.startswith(prefix) for prefix in valid_prefixes)
                    
                    if is_valid:
                        print(f"   ✅ Valid code: {code}")
                        valid_codes += 1
                    else:
                        print(f"   ❌ Invalid code: {code}")
                        issues.append(f"Invalid domain code: {code}")
                
                if valid_codes == len(domain_outcomes) and valid_codes > 0:
                    quality_score += 1
                    print(f"   🎯 DOMAIN CODES CRITERION: PASSED ({valid_codes}/{len(domain_outcomes)} codes valid)")
                else:
                    print(f"   ❌ DOMAIN CODES CRITERION: FAILED ({valid_codes}/{len(domain_outcomes)} codes valid)")
            
            # 4. CHECK: Assessment methods should be comprehensive (5-7 methods)
            print(f"\n4️⃣ ASSESSMENT METHODS ANALYSIS (Review Requirement: 5-7 methods):")
            assessment = blocks.get("assessment", [])
            assessment_count = len(assessment)
            
            if 5 <= assessment_count <= 7:
                quality_score += 1
                print(f"   ✅ Assessment methods: {assessment_count} (compliant)")
                print(f"   🎯 ASSESSMENT CRITERION: PASSED")
                for i, method in enumerate(assessment):
                    print(f"      {i+1}. {method}")
            else:
                print(f"   ⚠️ Assessment methods: {assessment_count} (should be 5-7)")
                print(f"   ❌ ASSESSMENT CRITERION: FAILED")
                warnings.append(f"Assessment has {assessment_count} methods (should be 5-7)")
            
            # 5. CHECK: Differentiation strategies should be included
            print(f"\n5️⃣ DIFFERENTIATION STRATEGIES ANALYSIS (Review Requirement: Must be included):")
            differentiation_found = 0
            
            # Check in activities
            for i, activity in enumerate(activities):
                if activity.get("differentiation"):
                    differentiation_found += 1
                    print(f"   ✅ Activity {i+1} has differentiation strategy")
            
            # Check in main differentiation section
            main_differentiation = data.get("differentiation", {})
            if main_differentiation:
                print(f"   ✅ Main differentiation section present")
                differentiation_found += 1
            
            if differentiation_found > 0:
                quality_score += 1
                print(f"   🎯 DIFFERENTIATION CRITERION: PASSED ({differentiation_found} instances found)")
            else:
                print(f"   ❌ DIFFERENTIATION CRITERION: FAILED (no differentiation strategies found)")
                issues.append("No differentiation strategies found")
            
            # 6. CHECK: Family/community involvement suggestions should be present
            print(f"\n6️⃣ FAMILY/COMMUNITY INVOLVEMENT ANALYSIS (Review Requirement: Must be present):")
            family_involvement = data.get("familyCommunityInvolvement")
            
            if family_involvement:
                quality_score += 1
                print(f"   ✅ Family/community involvement present")
                print(f"   🎯 FAMILY INVOLVEMENT CRITERION: PASSED")
                print(f"      Content: {family_involvement[:100]}...")
            else:
                print(f"   ❌ FAMILY INVOLVEMENT CRITERION: FAILED")
                issues.append("No family/community involvement suggestions found")
            
            # 7. CHECK: Theme relevance (Names and Identity theme)
            print(f"\n7️⃣ THEME RELEVANCE ANALYSIS (Review Requirement: Names and Identity theme):")
            theme_keywords = ["isim", "kimlik", "benlik", "tanı", "harf", "ad"]
            theme_relevance = 0
            
            # Check in activities
            for activity in activities:
                title = activity.get("title", "").lower()
                materials = str(activity.get("materials", [])).lower()
                steps = str(activity.get("steps", [])).lower()
                content = f"{title} {materials} {steps}"
                
                if any(keyword in content for keyword in theme_keywords):
                    theme_relevance += 1
            
            # Check in other sections
            plan_content = str(data).lower()
            theme_mentions = sum(1 for keyword in theme_keywords if keyword in plan_content)
            
            if theme_relevance > 0 or theme_mentions >= 3:
                quality_score += 1
                print(f"   ✅ Theme relevance found in {theme_relevance} activities, {theme_mentions} total mentions")
                print(f"   🎯 THEME RELEVANCE CRITERION: PASSED")
            else:
                print(f"   ❌ THEME RELEVANCE CRITERION: FAILED")
                issues.append("Plan does not adequately address 'Names and Identity' theme")
            
            # FINAL QUALITY ASSESSMENT
            print(f"\n" + "=" * 60)
            print(f"📊 FINAL QUALITY ASSESSMENT:")
            print(f"Quality Score: {quality_score}/{max_score} ({(quality_score/max_score)*100:.1f}%)")
            
            if issues:
                print(f"\n❌ CRITICAL ISSUES ({len(issues)}):")
                for issue in issues:
                    print(f"   • {issue}")
            
            if warnings:
                print(f"\n⚠️ WARNINGS ({len(warnings)}):")
                for warning in warnings:
                    print(f"   • {warning}")
            
            # PASS/FAIL DETERMINATION
            if quality_score >= 6:  # At least 6/7 criteria must pass
                print(f"\n✅ OVERALL RESULT: PASSED")
                print(f"   AI system prompt generates high-quality plans meeting review criteria")
                return True
            else:
                print(f"\n❌ OVERALL RESULT: FAILED")
                print(f"   AI system prompt needs improvement to meet review criteria")
                return False
                
        except Exception as e:
            print(f"❌ Test exception: {str(e)}")
            return False
    
    def run_quality_test(self):
        """Run the AI quality test as requested in review"""
        print("🚀 MaarifPlanner AI System Prompt Quality Test")
        print("=" * 60)
        print("Testing updated system prompt for plan quality as per review request")
        
        # Setup authentication
        if not self.setup_auth():
            return False
        
        # Run the main quality test
        result = self.test_ai_plan_quality_review_request()
        
        print(f"\n" + "=" * 60)
        if result:
            print("🎉 AI QUALITY TEST COMPLETED SUCCESSFULLY")
            print("The updated system prompt generates plans meeting PDF quality standards")
        else:
            print("❌ AI QUALITY TEST FAILED")
            print("The system prompt needs further improvements")
        
        return result

if __name__ == "__main__":
    tester = AIQualityTester()
    success = tester.run_quality_test()
    sys.exit(0 if success else 1)