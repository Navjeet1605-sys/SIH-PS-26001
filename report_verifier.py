"""
report_verifier.py
Automated NLP Report Verification Engine for NER-Vision Landslide Guardian.

Analyzes citizen hazard reports using word-based NLP, distress indicator scoring,
spam/noise filtering, and physical sensor telemetry cross-validation.
"""

import re
import data

# High-confidence disaster indicator keywords & phrases (weighted by severity)
CRITICAL_DISASTER_KEYWORDS = {
    # Direct landslide / slope failure words (Weight: 3.5)
    "landslide": 3.5, "mudslide": 3.5, "rockfall": 3.5, "debris flow": 3.5,
    "bhooskhalan": 3.5, "slide": 2.5, "earthfall": 3.0, "slope collapse": 3.5,
    
    # Ground & structural displacement words (Weight: 2.8)
    "crack": 2.8, "cracks": 2.8, "fissure": 3.0, "gaping crack": 3.2,
    "foundation shift": 3.0, "tilting pole": 2.8, "leaning tree": 2.5,
    "wall crack": 2.8, "road collapse": 3.2, "subsidence": 3.0, "sinking": 2.5,
    
    # Hydraulic & weather indicators (Weight: 2.2)
    "muddy water": 2.5, "brown spring": 2.5, "heavy rain": 2.2, "downpour": 2.2,
    "cloudburst": 3.0, "torrential": 2.2, "water gushing": 2.5, "flash flood": 2.8,
    
    # Physical impact & distress terms (Weight: 2.5)
    "trapped": 3.2, "blocked road": 2.8, "highway closed": 2.8, "nh-10": 2.5,
    "nh-27": 2.5, "debris": 2.2, "boulders": 2.5, "evacuating": 2.8,
    "buried": 3.5, "rumbling sound": 2.8, "popping rocks": 2.8, "help": 2.0
}

SPAM_KEYWORDS = [
    "test", "testing", "hello", "hi", "win money", "buy", "crypto", "offer",
    "http", "https", "fake", "random", "asdf", "1234", "dummy"
]


class ReportVerifier:
    @staticmethod
    def verify_report(description: str, location_id: str = None, reported_severity: str = "Medium"):
        desc_clean = (description or "").strip().lower()
        
        # 1. Spam & Length Filter
        if len(desc_clean) < 6:
            return {
                "verification_score": 0.15,
                "verification_status": "SUSPICIOUS_UNVERIFIED",
                "verification_reasons": ["Description too brief (< 6 characters) for physical hazard verification."],
                "is_verified": False
            }
            
        for spam_word in SPAM_KEYWORDS:
            if re.search(r'\b' + re.escape(spam_word) + r'\b', desc_clean) and len(desc_clean.split()) < 4:
                return {
                    "verification_score": 0.10,
                    "verification_status": "SUSPICIOUS_UNVERIFIED",
                    "verification_reasons": [f"Detected generic test/spam keyword: '{spam_word}'."],
                    "is_verified": False
                }

        # 2. NLP Word Implementation & Keyword Scoring
        score_accumulator = 0.0
        matched_indicators = []
        
        for keyword, weight in CRITICAL_DISASTER_KEYWORDS.items():
            if keyword in desc_clean:
                score_accumulator += weight
                matched_indicators.append(keyword)
                
        # Word count & descriptive context bonus
        words = desc_clean.split()
        if len(words) >= 8:
            score_accumulator += 1.0
        if len(words) >= 15:
            score_accumulator += 1.0

        reasons = []
        if matched_indicators:
            reasons.append(f"NLP matched {len(matched_indicators)} disaster indicators: [{', '.join(matched_indicators[:4])}].")
        else:
            reasons.append("No specific geological or slope failure keywords detected in report text.")

        # Normalize NLP base confidence score (0.0 to 1.0)
        nlp_confidence = min(0.85, score_accumulator / 7.0)

        # 3. Telemetry Cross-Validation with Sector Sensor State
        telemetry_boost = 0.0
        if location_id and location_id in [l["id"] for l in data.LOCATIONS]:
            try:
                state = data.get_state().get(location_id, {})
                rain_24h = state.get("rainfall_24h", 0)
                soil_moist = state.get("soil_moisture", 0)
                slope = state.get("slope_deg", 0)
                
                # Active heavy rain or saturated soil significantly boosts credibility
                if rain_24h >= 45.0 or soil_moist >= 65.0:
                    telemetry_boost += 0.20
                    reasons.append(f"Telemetry Cross-Check Confirmed: Active high rain ({rain_24h:.1f}mm/24h) & soil moisture ({soil_moist:.1f}%) in sector.")
                elif rain_24h >= 25.0:
                    telemetry_boost += 0.10
                    reasons.append(f"Telemetry Cross-Check: Moderate rainfall ({rain_24h:.1f}mm/24h) active at sector.")
                    
                if slope >= 35.0:
                    telemetry_boost += 0.05
            except Exception as e:
                pass

        # 4. Final Composite Verification Score calculation
        final_score = min(0.98, max(0.10, nlp_confidence + telemetry_boost))
        
        # High emergency reporting boost
        if reported_severity in ("High", "Very High") and final_score >= 0.45:
            final_score = min(0.98, final_score + 0.10)
            
        is_verified = final_score >= 0.55
        status = "VERIFIED_REAL" if is_verified else "SUSPICIOUS_UNVERIFIED"
        
        return {
            "verification_score": round(final_score, 2),
            "verification_status": status,
            "verification_reasons": reasons,
            "is_verified": is_verified
        }
