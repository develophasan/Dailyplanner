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

# Backend URL from environment - Updated for local testing as per review request
BACKEND_URL = "http://localhost:8001/api"

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
        """Test AI chat endpoint for complete plan content - CRITICAL TEST AS PER REVIEW REQUEST"""
        if not self.auth_token:
            self.log_test("AI Chat Content Completeness", False, "No auth token available")
            return False
            
        # EXACT REQUEST FROM REVIEW: "60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur"
        payload = {
            "message": "60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur",
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
            print(f"\n🔍 COMPREHENSIVE AI CONTENT ANALYSIS (Review Request):")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Store response for detailed analysis
            self.ai_response = data
            
            # CRITICAL CHECKS AS PER REVIEW REQUEST
            issues = []
            warnings = []
            
            # 1. Check finalize status
            if not data.get("finalize"):
                issues.append("Plan not finalized (finalize: false)")
            
            # 2. Check blocks object exists and is complete
            blocks = data.get("blocks", {})
            if not blocks:
                issues.append("Missing 'blocks' object")
                return self._log_content_test_result(issues, warnings, data)
            
            # 3. DETAILED ACTIVITIES VALIDATION (Review Requirement)
            activities = blocks.get("activities", [])
            if not activities or len(activities) == 0:
                issues.append("Empty 'blocks.activities' array")
            else:
                print(f"   📋 Found {len(activities)} activities")
                if len(activities) < 3:
                    warnings.append(f"Only {len(activities)} activities (recommended: minimum 3)")
                
                # Check each activity for detailed requirements
                for i, activity in enumerate(activities):
                    activity_issues = []
                    
                    # Required fields
                    if not activity.get("title"):
                        activity_issues.append("missing title")
                    if not activity.get("location"):
                        activity_issues.append("missing location")
                    if not activity.get("duration"):
                        activity_issues.append("missing duration")
                    if not activity.get("objectives"):
                        activity_issues.append("missing objectives")
                    if not activity.get("differentiation"):
                        activity_issues.append("missing differentiation")
                    
                    # Materials validation (Review Requirement: 5-8 items)
                    materials = activity.get("materials", [])
                    if not materials:
                        activity_issues.append("missing materials")
                    elif len(materials) < 5:
                        warnings.append(f"Activity {i+1} has only {len(materials)} materials (recommended: 5-8)")
                    elif len(materials) > 8:
                        warnings.append(f"Activity {i+1} has {len(materials)} materials (recommended: 5-8)")
                    else:
                        print(f"   ✅ Activity {i+1} materials: {len(materials)} items")
                    
                    # Steps validation (Review Requirement: 6-10 steps)
                    steps = activity.get("steps", [])
                    if not steps:
                        activity_issues.append("missing steps")
                    elif len(steps) < 6:
                        warnings.append(f"Activity {i+1} has only {len(steps)} steps (recommended: 6-10)")
                    elif len(steps) > 10:
                        warnings.append(f"Activity {i+1} has {len(steps)} steps (recommended: 6-10)")
                    else:
                        print(f"   ✅ Activity {i+1} steps: {len(steps)} items")
                    
                    # Mapping validation
                    if not activity.get("mapping"):
                        activity_issues.append("missing mapping")
                    
                    if activity_issues:
                        issues.append(f"Activity {i+1} ({activity.get('title', 'Untitled')}): {', '.join(activity_issues)}")
            
            # 4. ASSESSMENT VALIDATION (Review Requirement: 5-6 methods)
            assessment = blocks.get("assessment", [])
            if not assessment or len(assessment) == 0:
                issues.append("Empty 'blocks.assessment' array")
            else:
                print(f"   📊 Found {len(assessment)} assessment methods")
                if len(assessment) < 5:
                    warnings.append(f"Only {len(assessment)} assessment methods (recommended: 5-6)")
                elif len(assessment) > 6:
                    warnings.append(f"{len(assessment)} assessment methods (recommended: 5-6)")
                else:
                    print(f"   ✅ Assessment methods: {len(assessment)} items (optimal)")
            
            # 5. MEALS/CLEANUP VALIDATION (Review Requirement: 4-5 items)
            meals_cleanup = blocks.get("mealsCleanup", [])
            if not meals_cleanup or len(meals_cleanup) == 0:
                issues.append("Empty 'blocks.mealsCleanup' array")
            else:
                print(f"   🍽️ Found {len(meals_cleanup)} meals/cleanup items")
                if len(meals_cleanup) < 4:
                    warnings.append(f"Only {len(meals_cleanup)} meals/cleanup items (recommended: 4-5)")
                elif len(meals_cleanup) > 5:
                    warnings.append(f"{len(meals_cleanup)} meals/cleanup items (recommended: 4-5)")
                else:
                    print(f"   ✅ Meals/cleanup: {len(meals_cleanup)} items (optimal)")
            
            # 6. DOMAIN OUTCOMES VALIDATION (Review Requirement: 4-5 areas)
            domain_outcomes = data.get("domainOutcomes", [])
            if not domain_outcomes or len(domain_outcomes) == 0:
                issues.append("Empty 'domainOutcomes' array")
            else:
                print(f"   🎯 Found {len(domain_outcomes)} domain outcomes")
                if len(domain_outcomes) < 4:
                    warnings.append(f"Only {len(domain_outcomes)} domain outcomes (recommended: 4-5)")
                elif len(domain_outcomes) > 5:
                    warnings.append(f"{len(domain_outcomes)} domain outcomes (recommended: 4-5)")
                else:
                    print(f"   ✅ Domain outcomes: {len(domain_outcomes)} items (optimal)")
                
                # Check for proper Turkish educational codes (TADB, MAB, HSAB, SNAB, SDB)
                found_codes = set()
                for outcome in domain_outcomes:
                    code = outcome.get("code", "")
                    for prefix in ["TADB", "MAB", "HSAB", "SNAB", "SDB"]:
                        if prefix in code:
                            found_codes.add(prefix)
                            break
                
                print(f"   📚 Educational domains found: {', '.join(sorted(found_codes))}")
                if len(found_codes) < 4:
                    warnings.append(f"Only {len(found_codes)} educational domains covered (recommended: 4-5 from TADB, MAB, HSAB, SNAB, SDB)")
            
            # 7. CONCEPTUAL SKILLS VALIDATION (Review Requirement)
            conceptual_skills = data.get("conceptualSkills", [])
            if not conceptual_skills or len(conceptual_skills) == 0:
                issues.append("Missing 'conceptualSkills' array")
            else:
                print(f"   🧠 Found {len(conceptual_skills)} conceptual skills")
            
            # 8. DISPOSITIONS VALIDATION (Review Requirement)
            dispositions = data.get("dispositions", [])
            if not dispositions or len(dispositions) == 0:
                issues.append("Missing 'dispositions' array")
            else:
                print(f"   💭 Found {len(dispositions)} dispositions")
            
            return self._log_content_test_result(issues, warnings, data)
                
        except Exception as e:
            self.log_test("AI Chat Content Completeness", False, f"Exception: {str(e)}")
        
        return False
    
    def _log_content_test_result(self, issues, warnings, data):
        """Helper method to log comprehensive content test results"""
        blocks = data.get("blocks", {})
        activities = blocks.get("activities", [])
        assessment = blocks.get("assessment", [])
        domain_outcomes = data.get("domainOutcomes", [])
        conceptual_skills = data.get("conceptualSkills", [])
        dispositions = data.get("dispositions", [])
        meals_cleanup = blocks.get("mealsCleanup", [])
        
        if issues:
            details = f"CRITICAL ISSUES: {'; '.join(issues)}"
            if warnings:
                details += f" | WARNINGS: {'; '.join(warnings)}"
            self.log_test("AI Chat Content Completeness", False, details)
            print(f"❌ FAILED: {details}")
            return False
        else:
            success_details = f"✅ COMPREHENSIVE PLAN: {len(activities)} activities, {len(assessment)} assessments, {len(domain_outcomes)} domains, {len(conceptual_skills)} skills, {len(dispositions)} dispositions, {len(meals_cleanup)} meals/cleanup"
            if warnings:
                success_details += f" | Minor warnings: {'; '.join(warnings)}"
            self.log_test("AI Chat Content Completeness", True, success_details)
            print(f"✅ PASSED: {success_details}")
            return True

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
                print(f"🔍 Incomplete Info Response Analysis:")
                print(f"finalize: {data.get('finalize')}")
                print(f"followUpQuestions: {bool(data.get('followUpQuestions'))}")
                print(f"missingFields: {bool(data.get('missingFields'))}")
                
                # Should either ask follow-up questions or provide a basic plan
                has_follow_up = bool(data.get("followUpQuestions"))
                has_missing_fields = bool(data.get("missingFields"))
                is_finalized = data.get("finalize", False)
                
                if has_follow_up or has_missing_fields or not is_finalized:
                    details = f"AI properly handles incomplete info - finalize: {is_finalized}, followUp: {has_follow_up}, missing: {has_missing_fields}"
                    self.log_test("AI Chat Incomplete Info", True, details)
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

    def test_ai_comprehensive_plan_60_72_art_theme(self):
        """TEST SCENARIO 1: Request comprehensive daily plan for 60-72 age group with art theme"""
        if not self.auth_token:
            self.log_test("AI Comprehensive Plan 60-72 Art Theme", False, "No auth token available")
            return False
            
        payload = {
            "message": "60-72 ay yaş grubu için sanat temalı kapsamlı günlük plan hazırla. Boyama, yaratıcı sanat çalışmaları, renk kavramı ve el becerilerini geliştiren etkinlikler dahil et. Detaylı malzeme listesi, adım adım yönergeler ve değerlendirme yöntemleri ile birlikte hazırla.",
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("AI Comprehensive Plan 60-72 Art Theme", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            print(f"\n🎨 ART THEME PLAN ANALYSIS:")
            
            # Specific validations for art theme
            issues = []
            
            # Check if plan is finalized and complete
            if not data.get("finalize"):
                issues.append("Plan not finalized")
            
            # Check activities for art theme
            blocks = data.get("blocks", {})
            activities = blocks.get("activities", [])
            
            if len(activities) < 3:
                issues.append(f"Insufficient activities: {len(activities)} (minimum 3 required)")
            
            art_related_count = 0
            for activity in activities:
                title = activity.get("title", "").lower()
                materials = str(activity.get("materials", [])).lower()
                if any(keyword in title or keyword in materials for keyword in ["sanat", "boyama", "renk", "yaratıcı", "çizim", "boya"]):
                    art_related_count += 1
            
            if art_related_count == 0:
                issues.append("No art-related activities found")
            
            print(f"   🎨 Art-related activities: {art_related_count}/{len(activities)}")
            
            # Validate detailed requirements
            for i, activity in enumerate(activities):
                materials = activity.get("materials", [])
                steps = activity.get("steps", [])
                
                if len(materials) < 5 or len(materials) > 8:
                    issues.append(f"Activity {i+1} materials count: {len(materials)} (should be 5-8)")
                
                if len(steps) < 6 or len(steps) > 10:
                    issues.append(f"Activity {i+1} steps count: {len(steps)} (should be 6-10)")
                
                if not activity.get("duration"):
                    issues.append(f"Activity {i+1} missing duration")
                if not activity.get("objectives"):
                    issues.append(f"Activity {i+1} missing objectives")
                if not activity.get("differentiation"):
                    issues.append(f"Activity {i+1} missing differentiation")
            
            if issues:
                self.log_test("AI Comprehensive Plan 60-72 Art Theme", False, f"Issues: {'; '.join(issues)}")
                return False
            else:
                self.log_test("AI Comprehensive Plan 60-72 Art Theme", True, f"Complete art-themed plan with {len(activities)} activities, {art_related_count} art-related")
                return True
                
        except Exception as e:
            self.log_test("AI Comprehensive Plan 60-72 Art Theme", False, f"Exception: {str(e)}")
        
        return False

    def test_ai_detailed_plan_math_language(self):
        """TEST SCENARIO 2: Request detailed plan with math and language activities"""
        if not self.auth_token:
            self.log_test("AI Detailed Plan Math Language", False, "No auth token available")
            return False
            
        payload = {
            "message": "60-72 ay yaş grubu için matematik ve dil etkinlikleri içeren detaylı günlük plan hazırla. Sayı kavramı, geometrik şekiller, harf tanıma, dinleme becerileri ve kelime dağarcığı geliştirme odaklı. Her etkinlik için 5-8 malzeme, 6-10 adım, süre, hedefler ve bireysel farklılıklar için uyarlamalar dahil et.",
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("AI Detailed Plan Math Language", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            print(f"\n📚 MATH & LANGUAGE PLAN ANALYSIS:")
            
            issues = []
            
            # Check domain outcomes for math and language codes
            domain_outcomes = data.get("domainOutcomes", [])
            math_domains = [d for d in domain_outcomes if "MAB" in d.get("code", "")]
            language_domains = [d for d in domain_outcomes if "TADB" in d.get("code", "")]
            
            print(f"   📊 Math domains (MAB): {len(math_domains)}")
            print(f"   📝 Language domains (TADB): {len(language_domains)}")
            
            if len(math_domains) == 0:
                issues.append("No mathematics domain outcomes (MAB) found")
            if len(language_domains) == 0:
                issues.append("No language domain outcomes (TADB) found")
            
            # Check activities for math and language content
            blocks = data.get("blocks", {})
            activities = blocks.get("activities", [])
            
            math_activities = 0
            language_activities = 0
            
            for activity in activities:
                title = activity.get("title", "").lower()
                materials = str(activity.get("materials", [])).lower()
                steps = str(activity.get("steps", [])).lower()
                content = f"{title} {materials} {steps}"
                
                if any(keyword in content for keyword in ["matematik", "sayı", "geometri", "şekil", "sayma", "rakam"]):
                    math_activities += 1
                if any(keyword in content for keyword in ["dil", "harf", "kelime", "dinleme", "konuşma", "türkçe", "hikaye"]):
                    language_activities += 1
            
            print(f"   🔢 Math-related activities: {math_activities}")
            print(f"   📖 Language-related activities: {language_activities}")
            
            if math_activities == 0:
                issues.append("No math-related activities found")
            if language_activities == 0:
                issues.append("No language-related activities found")
            
            if issues:
                self.log_test("AI Detailed Plan Math Language", False, f"Issues: {'; '.join(issues)}")
                return False
            else:
                self.log_test("AI Detailed Plan Math Language", True, f"Complete math & language plan: {math_activities} math, {language_activities} language activities")
                return True
                
        except Exception as e:
            self.log_test("AI Detailed Plan Math Language", False, f"Exception: {str(e)}")
        
        return False

    def test_ai_response_structure_validation(self):
        """TEST SCENARIO 3: Verify response structure matches enhanced template"""
        if not self.auth_token:
            self.log_test("AI Response Structure Validation", False, "No auth token available")
            return False
            
        payload = {
            "message": "60-72 ay yaş grubu için kapsamlı günlük plan hazırla. Tüm alanları detayca doldur.",
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("AI Response Structure Validation", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            print(f"\n🏗️ STRUCTURE VALIDATION:")
            
            # Required top-level fields
            required_fields = ["finalize", "type", "ageBand", "date", "domainOutcomes", "blocks"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log_test("AI Response Structure Validation", False, f"Missing required fields: {', '.join(missing_fields)}")
                return False
            
            # Check blocks structure
            blocks = data.get("blocks", {})
            required_block_fields = ["startOfDay", "activities", "assessment"]
            missing_block_fields = [field for field in required_block_fields if field not in blocks]
            
            if missing_block_fields:
                self.log_test("AI Response Structure Validation", False, f"Missing blocks fields: {', '.join(missing_block_fields)}")
                return False
            
            # Validate activities structure
            activities = blocks.get("activities", [])
            if not activities:
                self.log_test("AI Response Structure Validation", False, "Empty activities array")
                return False
            
            activity_structure_issues = []
            for i, activity in enumerate(activities):
                required_activity_fields = ["title", "location", "materials", "steps", "mapping"]
                missing_activity_fields = [field for field in required_activity_fields if field not in activity]
                if missing_activity_fields:
                    activity_structure_issues.append(f"Activity {i+1} missing: {', '.join(missing_activity_fields)}")
            
            if activity_structure_issues:
                self.log_test("AI Response Structure Validation", False, f"Activity structure issues: {'; '.join(activity_structure_issues)}")
                return False
            
            # Check optional but recommended fields
            optional_fields = ["conceptualSkills", "dispositions", "crossComponents", "contentFrame"]
            present_optional = [field for field in optional_fields if field in data and data[field]]
            
            print(f"   ✅ Required fields: All present")
            print(f"   📋 Activities: {len(activities)} with complete structure")
            print(f"   🎯 Optional fields present: {len(present_optional)}/{len(optional_fields)}")
            
            self.log_test("AI Response Structure Validation", True, f"Complete structure with {len(activities)} activities, {len(present_optional)} optional fields")
            return True
                
        except Exception as e:
            self.log_test("AI Response Structure Validation", False, f"Exception: {str(e)}")
        
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

    # NEW DEVELOPMENT TESTS - As requested in review
    def test_ai_chat_automatic_date_usage(self):
        """Test AI Chat automatic use of today's date - NEW DEVELOPMENT"""
        if not self.auth_token:
            self.log_test("AI Chat Automatic Date Usage", False, "No auth token available")
            return False
            
        payload = {
            "message": "60-72 ay çocukları için isimler ve kimlik teması günlük plan oluştur",
            "history": [],
            "ageBand": "60_72",
            "planType": "daily"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("AI Chat Automatic Date Usage", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            today_date = datetime.utcnow().strftime("%Y-%m-%d")
            plan_date = data.get("date", "")
            
            print(f"\n📅 AUTOMATIC DATE USAGE TEST:")
            print(f"   Today's date: {today_date}")
            print(f"   Plan date: {plan_date}")
            
            if plan_date == today_date:
                self.log_test("AI Chat Automatic Date Usage", True, f"AI automatically used today's date: {plan_date}")
                return True
            else:
                self.log_test("AI Chat Automatic Date Usage", False, f"AI used {plan_date} instead of today's date {today_date}")
                return False
                
        except Exception as e:
            self.log_test("AI Chat Automatic Date Usage", False, f"Exception: {str(e)}")
        
        return False

    def test_ai_chat_automatic_age_usage(self):
        """Test AI Chat automatic use of user's ageDefault - NEW DEVELOPMENT"""
        if not self.auth_token:
            self.log_test("AI Chat Automatic Age Usage", False, "No auth token available")
            return False
            
        # First get user info to check ageDefault
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            user_response = requests.get(f"{self.base_url}/auth/me", headers=headers)
            
            if user_response.status_code != 200:
                self.log_test("AI Chat Automatic Age Usage", False, "Could not get user info")
                return False
                
            user_data = user_response.json()
            user_age_default = user_data.get("ageDefault", "60_72")
            
            # Now test AI chat without specifying ageBand
            payload = {
                "message": "Matematik temalı günlük plan oluştur",
                "history": [],
                "planType": "daily"
                # Note: Not specifying ageBand to test automatic usage
            }
            
            response = requests.post(f"{self.base_url}/ai/chat", json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("AI Chat Automatic Age Usage", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            plan_age_band = data.get("ageBand", "")
            
            print(f"\n👶 AUTOMATIC AGE USAGE TEST:")
            print(f"   User's ageDefault: {user_age_default}")
            print(f"   Plan ageBand: {plan_age_band}")
            
            if plan_age_band == user_age_default:
                self.log_test("AI Chat Automatic Age Usage", True, f"AI automatically used user's age group: {plan_age_band}")
                return True
            else:
                self.log_test("AI Chat Automatic Age Usage", False, f"AI used {plan_age_band} instead of user's default {user_age_default}")
                return False
                
        except Exception as e:
            self.log_test("AI Chat Automatic Age Usage", False, f"Exception: {str(e)}")
        
        return False

    def test_daily_plan_delete(self):
        """Test DELETE /api/plans/daily/{plan_id} - NEW DEVELOPMENT"""
        if not self.auth_token:
            self.log_test("Daily Plan Delete", False, "No auth token available")
            return False
            
        # First create a plan to delete
        today = datetime.now().strftime("%Y-%m-%d")
        create_payload = {
            "date": today,
            "ageBand": "60_72",
            "title": "Test Plan for Deletion",
            "planJson": {
                "type": "daily",
                "ageBand": "60_72",
                "date": today,
                "finalize": True,
                "domainOutcomes": [{"code": "MAB.1", "indicators": ["Test"], "notes": "Test"}],
                "blocks": {
                    "startOfDay": "Test",
                    "activities": [{"title": "Test Activity", "location": "Test", "materials": ["Test"], "steps": ["Test"]}],
                    "assessment": ["Test assessment"]
                }
            }
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create plan
            create_response = requests.post(f"{self.base_url}/plans/daily", json=create_payload, headers=headers)
            
            if create_response.status_code != 200:
                self.log_test("Daily Plan Delete", False, f"Failed to create test plan: {create_response.status_code}")
                return False
                
            plan_data = create_response.json()
            plan_id = plan_data.get("id")
            
            if not plan_id:
                self.log_test("Daily Plan Delete", False, "No plan ID returned from create")
                return False
            
            print(f"\n🗑️ DAILY PLAN DELETE TEST:")
            print(f"   Created plan ID: {plan_id}")
            
            # Now delete the plan
            delete_response = requests.delete(f"{self.base_url}/plans/daily/{plan_id}", headers=headers)
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                if "message" in delete_data:
                    # Verify plan is actually deleted by trying to get it
                    get_response = requests.get(f"{self.base_url}/plans/daily/{plan_id}", headers=headers)
                    if get_response.status_code == 404:
                        self.log_test("Daily Plan Delete", True, f"Plan {plan_id} successfully deleted")
                        return True
                    else:
                        self.log_test("Daily Plan Delete", False, f"Plan still exists after deletion (HTTP {get_response.status_code})")
                        return False
                else:
                    self.log_test("Daily Plan Delete", False, "Missing message in delete response")
                    return False
            else:
                self.log_test("Daily Plan Delete", False, f"HTTP {delete_response.status_code}: {delete_response.text}")
                return False
                
        except Exception as e:
            self.log_test("Daily Plan Delete", False, f"Exception: {str(e)}")
        
        return False

    def test_monthly_plan_delete(self):
        """Test DELETE /api/plans/monthly/{plan_id} - NEW DEVELOPMENT"""
        if not self.auth_token:
            self.log_test("Monthly Plan Delete", False, "No auth token available")
            return False
            
        # First create a monthly plan to delete
        current_month = datetime.now().strftime("%Y-%m")
        create_payload = {
            "month": current_month,
            "ageBand": "60_72",
            "title": "Test Monthly Plan for Deletion",
            "planJson": {
                "type": "monthly",
                "ageBand": "60_72",
                "month": current_month,
                "themes": ["Test Theme"],
                "weeklyGoals": ["Test Goal"]
            }
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create monthly plan
            create_response = requests.post(f"{self.base_url}/plans/monthly", json=create_payload, headers=headers)
            
            if create_response.status_code != 200:
                self.log_test("Monthly Plan Delete", False, f"Failed to create test monthly plan: {create_response.status_code}")
                return False
                
            plan_data = create_response.json()
            plan_id = plan_data.get("id")
            
            if not plan_id:
                self.log_test("Monthly Plan Delete", False, "No plan ID returned from create")
                return False
            
            print(f"\n🗑️ MONTHLY PLAN DELETE TEST:")
            print(f"   Created monthly plan ID: {plan_id}")
            
            # Now delete the monthly plan
            delete_response = requests.delete(f"{self.base_url}/plans/monthly/{plan_id}", headers=headers)
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                if "message" in delete_data:
                    self.log_test("Monthly Plan Delete", True, f"Monthly plan {plan_id} successfully deleted")
                    return True
                else:
                    self.log_test("Monthly Plan Delete", False, "Missing message in delete response")
                    return False
            else:
                self.log_test("Monthly Plan Delete", False, f"HTTP {delete_response.status_code}: {delete_response.text}")
                return False
                
        except Exception as e:
            self.log_test("Monthly Plan Delete", False, f"Exception: {str(e)}")
        
        return False

    def test_portfolio_photo_upload(self):
        """Test POST /api/plans/daily/{plan_id}/portfolio - NEW DEVELOPMENT"""
        if not self.auth_token:
            self.log_test("Portfolio Photo Upload", False, "No auth token available")
            return False
            
        # First create a daily plan for portfolio
        if not hasattr(self, 'plan_id'):
            # Create a plan if we don't have one
            today = datetime.now().strftime("%Y-%m-%d")
            create_payload = {
                "date": today,
                "ageBand": "60_72",
                "title": "Test Plan for Portfolio",
                "planJson": {
                    "type": "daily",
                    "ageBand": "60_72",
                    "date": today,
                    "finalize": True,
                    "domainOutcomes": [{"code": "MAB.1", "indicators": ["Test"], "notes": "Test"}],
                    "blocks": {
                        "startOfDay": "Test",
                        "activities": [{"title": "Sanat Etkinliği", "location": "Sanat merkezi", "materials": ["Boya"], "steps": ["Boyama"]}],
                        "assessment": ["Fotoğraf"]
                    }
                }
            }
            
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                create_response = requests.post(f"{self.base_url}/plans/daily", json=create_payload, headers=headers)
                
                if create_response.status_code != 200:
                    self.log_test("Portfolio Photo Upload", False, f"Failed to create test plan: {create_response.status_code}")
                    return False
                    
                plan_data = create_response.json()
                self.plan_id = plan_data.get("id")
                
            except Exception as e:
                self.log_test("Portfolio Photo Upload", False, f"Exception creating plan: {str(e)}")
                return False
        
        # Sample base64 image (1x1 pixel PNG)
        sample_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77zgAAAABJRU5ErkJggg=="
        
        portfolio_payload = {
            "planId": self.plan_id,
            "activityTitle": "Sanat Etkinliği",
            "photoBase64": sample_base64,
            "description": "Çocuğun boyama çalışması"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/plans/daily/{self.plan_id}/portfolio", json=portfolio_payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "message" in data:
                    self.portfolio_photo_id = data["id"]
                    print(f"\n📸 PORTFOLIO PHOTO UPLOAD TEST:")
                    print(f"   Uploaded photo ID: {data['id']}")
                    self.log_test("Portfolio Photo Upload", True, f"Portfolio photo uploaded with ID: {data['id']}")
                    return True
                else:
                    self.log_test("Portfolio Photo Upload", False, "Missing id or message in response")
                    return False
            else:
                self.log_test("Portfolio Photo Upload", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Portfolio Photo Upload", False, f"Exception: {str(e)}")
        
        return False

    def test_portfolio_photos_get(self):
        """Test GET /api/plans/daily/{plan_id}/portfolio - NEW DEVELOPMENT"""
        if not self.auth_token:
            self.log_test("Portfolio Photos Get", False, "No auth token available")
            return False
            
        if not hasattr(self, 'plan_id'):
            self.log_test("Portfolio Photos Get", False, "No plan ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/plans/daily/{self.plan_id}/portfolio", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"\n📷 PORTFOLIO PHOTOS GET TEST:")
                    print(f"   Retrieved {len(data)} portfolio photos")
                    
                    # Check structure of photos
                    if len(data) > 0:
                        photo = data[0]
                        required_fields = ["id", "activityTitle", "photoBase64", "uploadedAt"]
                        missing_fields = [field for field in required_fields if field not in photo]
                        
                        if missing_fields:
                            self.log_test("Portfolio Photos Get", False, f"Missing fields in photo: {', '.join(missing_fields)}")
                            return False
                    
                    self.log_test("Portfolio Photos Get", True, f"Retrieved {len(data)} portfolio photos with correct structure")
                    return True
                else:
                    self.log_test("Portfolio Photos Get", False, "Response is not a list")
                    return False
            else:
                self.log_test("Portfolio Photos Get", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Portfolio Photos Get", False, f"Exception: {str(e)}")
        
        return False

    def test_portfolio_photo_delete(self):
        """Test DELETE /portfolio/{photo_id} - NEW DEVELOPMENT"""
        if not self.auth_token:
            self.log_test("Portfolio Photo Delete", False, "No auth token available")
            return False
            
        if not hasattr(self, 'portfolio_photo_id'):
            self.log_test("Portfolio Photo Delete", False, "No portfolio photo ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.delete(f"{self.base_url}/portfolio/{self.portfolio_photo_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    print(f"\n🗑️ PORTFOLIO PHOTO DELETE TEST:")
                    print(f"   Deleted photo ID: {self.portfolio_photo_id}")
                    self.log_test("Portfolio Photo Delete", True, f"Portfolio photo {self.portfolio_photo_id} successfully deleted")
                    return True
                else:
                    self.log_test("Portfolio Photo Delete", False, "Missing message in delete response")
                    return False
            else:
                self.log_test("Portfolio Photo Delete", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Portfolio Photo Delete", False, f"Exception: {str(e)}")
        
        return False
    
    def run_all_tests(self):
        """Run all backend tests in order"""
        print("🚀 Starting MaarifPlanner Backend API Tests - NEW DEVELOPMENTS FOCUS")
        print("=" * 70)
        
        # High Priority Tests
        print("\n📋 HIGH PRIORITY TESTS:")
        self.test_auth_register()
        self.test_auth_login()
        self.test_auth_me()
        self.test_ai_chat_basic()
        self.test_daily_plans_create()
        self.test_daily_plans_list()
        self.test_daily_plans_get_by_id()
        
        # NEW DEVELOPMENTS TESTS (as requested in review)
        print("\n🆕 NEW DEVELOPMENTS TESTS (Review Request Focus):")
        print("   Testing AI Chat improvements, Plan Delete APIs, and Portfolio APIs")
        self.test_ai_chat_automatic_date_usage()
        self.test_ai_chat_automatic_age_usage()
        self.test_daily_plan_delete()
        self.test_monthly_plan_delete()
        self.test_portfolio_photo_upload()
        self.test_portfolio_photos_get()
        self.test_portfolio_photo_delete()
        
        # CRITICAL AI CONTENT QUALITY TESTS (as requested in review)
        print("\n🎯 CRITICAL AI CONTENT QUALITY TESTS (Review Request):")
        self.test_ai_chat_content_completeness()
        self.test_ai_comprehensive_plan_60_72_art_theme()
        self.test_ai_detailed_plan_math_language()
        self.test_ai_response_structure_validation()
        self.test_ai_chat_multiple_calls_consistency()
        self.test_ai_chat_incomplete_info_handling()
        
        # Medium Priority Tests
        print("\n📋 MEDIUM PRIORITY TESTS:")
        self.test_monthly_plans_create()
        self.test_monthly_plans_list()
        self.test_matrix_search()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY:")
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        # Separate NEW DEVELOPMENTS results
        new_dev_tests = [
            "AI Chat Automatic Date Usage",
            "AI Chat Automatic Age Usage", 
            "Daily Plan Delete",
            "Monthly Plan Delete",
            "Portfolio Photo Upload",
            "Portfolio Photos Get",
            "Portfolio Photo Delete"
        ]
        
        new_dev_passed = sum(1 for result in self.test_results if result["test"] in new_dev_tests and result["success"])
        new_dev_total = sum(1 for result in self.test_results if result["test"] in new_dev_tests)
        
        print(f"\n🆕 NEW DEVELOPMENTS SUMMARY:")
        print(f"✅ New Features Passed: {new_dev_passed}/{new_dev_total}")
        print(f"❌ New Features Failed: {new_dev_total - new_dev_passed}/{new_dev_total}")
        
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