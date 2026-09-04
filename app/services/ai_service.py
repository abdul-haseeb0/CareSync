import os
import json
import time
import urllib.request
import urllib.error
from config import Config
from logger_service import log_application, log_error

DISCLAIMER = "⚠️ AI-Generated Analysis. Human-in-the-Loop required. Must be reviewed by a licensed medical professional."

class AIService:
    @staticmethod
    def _resolve_provider_and_key():
        provider = (Config.AI_PROVIDER or 'mock').strip().lower()
        if provider in ['gemini', 'google']:
            provider = 'google'
            api_key = Config.GOOGLE_API_KEY or Config.AI_API_KEY
        elif provider == 'groq':
            api_key = Config.GROQ_API_KEY or Config.AI_API_KEY
        elif provider == 'openai':
            api_key = Config.OPENAI_API_KEY or Config.AI_API_KEY
        else:
            api_key = Config.AI_API_KEY
        return provider, api_key

    @staticmethod
    def analyze_radiology(image_path=None, image_bytes=None, modality="X-Ray", body_part="Chest", clinical_notes=""):
        """
        Analyzes imaging scan (X-Ray, MRI, CT Scan) and returns structured diagnostic JSON.
        """
        provider, api_key = AIService._resolve_provider_and_key()
        
        if api_key and provider in ['groq', 'openai', 'google']:
            try:
                result = AIService._call_remote_radiology(provider, api_key, image_path, modality, body_part, clinical_notes)
                if result:
                    result['provider'] = provider
                    result['model'] = Config.AI_MODEL
                    return result
            except Exception as e:
                log_error(f"Remote AI Radiology provider '{provider}' failed, falling back to realistic diagnostic simulation: {e}")
                
        # Structured mock response
        mock = AIService._mock_radiology_analysis(modality, body_part, clinical_notes, image_path)
        mock['provider'] = 'mock'
        mock['model'] = 'CareSync Clinical Engine (Mock)'
        return mock

    @staticmethod
    def analyze_lab_report(raw_text="", file_path=None, test_type="Comprehensive Blood Panel"):
        """
        Analyzes laboratory reports (Blood panel, Urinalysis, Pathology) and returns structured interpretations.
        """
        provider, api_key = AIService._resolve_provider_and_key()
        
        if api_key and provider in ['groq', 'openai', 'google']:
            try:
                result = AIService._call_remote_lab(provider, api_key, raw_text, file_path, test_type)
                if result:
                    result['provider'] = provider
                    result['model'] = Config.AI_MODEL
                    return result
            except Exception as e:
                log_error(f"Remote AI Lab provider '{provider}' failed, falling back to realistic simulation: {e}")
                
        mock = AIService._mock_lab_analysis(raw_text, test_type)
        mock['provider'] = 'mock'
        mock['model'] = 'CareSync Clinical Engine (Mock)'
        return mock

    @staticmethod
    def clinical_assistant(vitals=None, chief_complaint="", symptoms="", medical_history="", current_medications=""):
        """
        Generates clinical suggestions (Diagnoses, Recommended tests, Treatment plans, Dosage warnings).
        """
        provider, api_key = AIService._resolve_provider_and_key()
        
        if api_key and provider in ['groq', 'openai', 'google']:
            try:
                result = AIService._call_remote_clinical(provider, api_key, vitals, chief_complaint, symptoms, medical_history, current_medications)
                if result:
                    result['provider'] = provider
                    result['model'] = Config.AI_MODEL
                    return result
            except Exception as e:
                log_error(f"Remote AI Clinical Assistant provider '{provider}' failed, falling back to realistic simulation: {e}")
                
        mock = AIService._mock_clinical_assistant(vitals, chief_complaint, symptoms, medical_history, current_medications)
        mock['provider'] = 'mock'
        mock['model'] = 'CareSync Clinical Engine (Mock)'
        return mock

    # =========================================================================
    # REAL REMOTE API IMPLEMENTATIONS (GROQ / OPENAI / GOOGLE GEMINI)
    # =========================================================================
    @staticmethod
    def _call_remote_radiology(provider, api_key, image_path, modality, body_part, clinical_notes):
        prompt = f"""You are an expert AI Radiologist assisting a medical doctor.
Modality: {modality}
Body Part: {body_part}
Clinical Context: {clinical_notes}

Analyze this radiographic case and respond ONLY with a raw, valid JSON object in this exact schema (no markdown formatting, no backticks):
{{
  "modality": "{modality}",
  "body_part": "{body_part}",
  "key_findings": ["string", "string"],
  "primary_diagnosis": "string",
  "confidence_score": 0.92,
  "differential_diagnoses": [
     {{"condition": "string", "probability": "High/Medium/Low", "notes": "string"}}
  ],
  "treatment_suggestions": ["string", "string"],
  "recommended_next_steps": ["string", "string"],
  "safety_warning": "{DISCLAIMER}"
}}"""

        if provider == 'groq':
            return AIService._call_groq_api(api_key, prompt)
        elif provider == 'google':
            return AIService._call_gemini_api(api_key, prompt)
        elif provider == 'openai':
            return AIService._call_openai_api(api_key, prompt)
        return None

    @staticmethod
    def _call_remote_lab(provider, api_key, raw_text, file_path, test_type):
        prompt = f"""You are an expert AI Clinical Pathologist.
Test Type: {test_type}
Lab Report Content/Values:
{raw_text}

Analyze and return ONLY a raw, valid JSON object in this exact schema (no markdown backticks):
{{
  "test_type": "{test_type}",
  "parameters": [
    {{"name": "Parameter Name", "value": "12.4", "unit": "mg/dL or other", "reference_range": "4.5-11.0", "status": "High/Low/Normal", "critical": false}}
  ],
  "abnormal_findings_summary": ["string"],
  "primary_interpretation": "string",
  "potential_causes": ["string"],
  "clinical_action_items": ["string"],
  "safety_warning": "{DISCLAIMER}"
}}"""

        if provider == 'groq':
            return AIService._call_groq_api(api_key, prompt)
        elif provider == 'google':
            return AIService._call_gemini_api(api_key, prompt)
        elif provider == 'openai':
            return AIService._call_openai_api(api_key, prompt)
        return None

    @staticmethod
    def _call_remote_clinical(provider, api_key, vitals, chief_complaint, symptoms, medical_history, current_medications):
        prompt = f"""You are an expert Clinical Decision Support AI Assistant.
Vitals: {json.dumps(vitals)}
Chief Complaint: {chief_complaint}
Symptoms: {symptoms}
Medical History: {medical_history}
Current Medications: {current_medications}

Generate clinical suggestions and return ONLY a raw, valid JSON object in this exact schema (no markdown backticks):
{{
  "potential_diagnoses": [
    {{"diagnosis": "string", "likelihood": "High/Moderate/Low", "rationale": "string"}}
  ],
  "recommended_tests": ["string", "string"],
  "suggested_treatment_plan": [
    {{"medication": "string", "dosage": "string", "frequency": "string", "duration": "string", "warning": "string"}}
  ],
  "clinical_summary": "string",
  "safety_warning": "{DISCLAIMER}"
}}"""

        if provider == 'groq':
            return AIService._call_groq_api(api_key, prompt)
        elif provider == 'google':
            return AIService._call_gemini_api(api_key, prompt)
        elif provider == 'openai':
            return AIService._call_openai_api(api_key, prompt)
        return None

    @staticmethod
    def _execute_with_retry(req, max_retries=3, backoff_factor=1.5):
        """
        Executes an HTTP request with automatic retry logic on HTTP 503 (Service Unavailable)
        or 429 (Too Many Requests) / transient network errors.
        """
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    return resp.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                last_exception = e
                # Retry on 503 Service Unavailable or 429 Rate Limit
                if e.code in [503, 429, 502, 504] and attempt < max_retries:
                    sleep_time = backoff_factor ** attempt
                    log_application(f"AI API returned HTTP {e.code}. Retrying in {sleep_time:.1f}s (Attempt {attempt}/{max_retries})...", "warning")
                    time.sleep(sleep_time)
                else:
                    raise e
            except (urllib.error.URLError, TimeoutError) as e:
                last_exception = e
                if attempt < max_retries:
                    sleep_time = backoff_factor ** attempt
                    log_application(f"AI API network timeout/error: {e}. Retrying in {sleep_time:.1f}s (Attempt {attempt}/{max_retries})...", "warning")
                    time.sleep(sleep_time)
                else:
                    raise e
        raise last_exception

    @staticmethod
    def _clean_json_markdown(text):
        cleaned = text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    @staticmethod
    def _call_groq_api(api_key, prompt):
        model = Config.AI_MODEL if Config.AI_MODEL and not any(k in Config.AI_MODEL for k in ['gemini', 'gpt']) else 'llama-3.3-70b-versatile'
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a clinical AI assistant. You must output only valid, parseable JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        resp_text = AIService._execute_with_retry(req)
        data = json.loads(resp_text)
        content = data['choices'][0]['message']['content']
        cleaned = AIService._clean_json_markdown(content)
        return json.loads(cleaned)

    @staticmethod
    def _call_openai_api(api_key, prompt):
        model = Config.AI_MODEL if Config.AI_MODEL and 'gpt' in Config.AI_MODEL else "gpt-4o"
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a medical AI specialist. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        resp_text = AIService._execute_with_retry(req)
        data = json.loads(resp_text)
        content = data['choices'][0]['message']['content']
        cleaned = AIService._clean_json_markdown(content)
        return json.loads(cleaned)

    @staticmethod
    def _call_gemini_api(api_key, prompt):
        model = Config.AI_MODEL if Config.AI_MODEL and 'gemini' in Config.AI_MODEL else 'gemini-2.5-flash'
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        resp_text = AIService._execute_with_retry(req)
        data = json.loads(resp_text)
        candidate = data['candidates'][0]['content']['parts'][0]['text']
        cleaned = AIService._clean_json_markdown(candidate)
        return json.loads(cleaned)

    # =========================================================================
    # ROBUST STRUCTURED MOCK GENERATORS (Zero crash, Realistic medical simulation)
    # =========================================================================
    @staticmethod
    def _mock_radiology_analysis(modality, body_part, clinical_notes, image_path):
        modality_lower = modality.lower()
        body_part_lower = body_part.lower() if body_part else "chest"
        
        if "chest" in body_part_lower or "lung" in body_part_lower:
            key_findings = [
                "Bilateral clear lung fields with subtle focal opacity in the right lower lobe.",
                "Cardiothoracic ratio within normal limits (< 0.50).",
                "No evidence of pleural effusion or pneumothorax.",
                "Costophrenic angles are sharp and well-defined."
            ]
            primary_diag = "Right Lower Lobe Community-Acquired Pneumonia (Early Stage)"
            diff_diag = [
                {"condition": "Viral Pneumonitis", "probability": "Moderate", "notes": "Correlate with inflammatory markers and viral PCR."},
                {"condition": "Localized Atelectasis", "probability": "Low", "notes": "No significant mediastinal shift noted."}
            ]
            treatment = [
                "Initiate empiric oral antimicrobial coverage (e.g., Amoxicillin-Clavulanate or Azithromycin as indicated).",
                "Adequate oral hydration, rest, and antipyretics for fever control.",
                "Follow-up chest radiograph in 4-6 weeks to ensure resolution."
            ]
            next_steps = [
                "Complete Blood Count (CBC) and C-Reactive Protein (CRP) testing.",
                "Pulse oximetry monitoring for SpO2 desaturation."
            ]
        elif "brain" in body_part_lower or "head" in body_part_lower:
            key_findings = [
                "Symmetrical cerebral hemispheres with normal gray-white matter differentiation.",
                "No acute intracranial hemorrhage or midline shift detected.",
                "Ventricular system and basal cisterns are normal in size and configuration."
            ]
            primary_diag = "Normal Non-Contrast Neuroimaging / Tension Cephalea"
            diff_diag = [
                {"condition": "Migraine without Aura", "probability": "High", "notes": "Clinical correlation with photophobia and headache diary required."},
                {"condition": "Cervicogenic Headache", "probability": "Moderate", "notes": "Assess neck range of motion and muscle spasm."}
            ]
            treatment = [
                "Supportive analgesia (NSAIDs / Paracetamol) as appropriate.",
                "Trigger identification and stress management."
            ]
            next_steps = [
                "Neurological follow-up if refractory symptoms persist.",
                "Keep a structured headache frequency log."
            ]
        elif "bone" in body_part_lower or "extremity" in body_part_lower or "leg" in body_part_lower or "arm" in body_part_lower:
            key_findings = [
                "Intact cortical margins without evidence of acute fracture or dislocation.",
                "Normal articular alignment and joint space preservation.",
                "Soft tissues show mild diffuse peri-articular edema without foreign bodies."
            ]
            primary_diag = "Soft Tissue Contusion / Acute Joint Sprain (Grade I)"
            diff_diag = [
                {"condition": "Non-Displaced Microfracture", "probability": "Low", "notes": "Consider MRI or repeat X-ray in 10-14 days if focal point tenderness persists."},
                {"condition": "Tendon Strain", "probability": "Moderate", "notes": "Correlate with active resistance testing."}
            ]
            treatment = [
                "R.I.C.E. protocol (Rest, Ice, Compression, Elevation).",
                "Short course of NSAIDs for pain and inflammation."
            ]
            next_steps = [
                "Weight-bearing as tolerated with supportive brace.",
                "Physical therapy evaluation if functional impairment exceeds 2 weeks."
            ]
        else:
            key_findings = [
                "Standard radiographic appearance for target anatomical zone.",
                "No focal lesions, calcifications, or structural disruption identified.",
                "Normal vascular and soft tissue margins."
            ]
            primary_diag = f"Unremarkable {modality} Study of {body_part}"
            diff_diag = [
                {"condition": "Non-Specific Musculoskeletal Discomfort", "probability": "Moderate", "notes": "Clinical examination correlation recommended."}
            ]
            treatment = ["Supportive symptomatic management and physical observation."]
            next_steps = ["Review clinical progress in 7-10 days if symptoms fail to resolve."]

        return {
            "modality": modality,
            "body_part": body_part,
            "key_findings": key_findings,
            "primary_diagnosis": primary_diag,
            "confidence_score": 0.91,
            "differential_diagnoses": diff_diag,
            "treatment_suggestions": treatment,
            "recommended_next_steps": next_steps,
            "safety_warning": DISCLAIMER
        }

    @staticmethod
    def _mock_lab_analysis(raw_text, test_type):
        text_lower = raw_text.lower() if raw_text else ""
        
        if "cbc" in text_lower or "blood" in test_type.lower() or "hematology" in text_lower or "hemoglobin" in text_lower:
            params = [
                {"name": "White Blood Cells (WBC)", "value": "13.8", "unit": "x10^3/uL", "reference_range": "4.5 - 11.0", "status": "High", "critical": False},
                {"name": "Hemoglobin (Hb)", "value": "14.2", "unit": "g/dL", "reference_range": "13.5 - 17.5", "status": "Normal", "critical": False},
                {"name": "Platelets", "value": "275", "unit": "x10^3/uL", "reference_range": "150 - 450", "status": "Normal", "critical": False},
                {"name": "C-Reactive Protein (CRP)", "value": "28.5", "unit": "mg/L", "reference_range": "< 5.0", "status": "High", "critical": False},
                {"name": "Neutrophils (%)", "value": "78.0", "unit": "%", "reference_range": "40.0 - 70.0", "status": "High", "critical": False}
            ]
            abnormal = [
                "Leukocytosis (WBC 13.8 x10^3/uL) with absolute neutrophilia (78%).",
                "Significantly elevated C-Reactive Protein (28.5 mg/L), indicating active systemic inflammation."
            ]
            interpretation = "Acute bacterial or inflammatory response pattern. Hematocrit and platelet counts remain within normal physiological ranges."
            causes = [
                "Bacterial respiratory or soft-tissue infection",
                "Systemic inflammatory response",
                "Early occult inflammatory process"
            ]
            actions = [
                "Correlate with vital signs (fever, heart rate) and physical examination.",
                "Initiate appropriate targeted antimicrobial therapy if bacterial infection is clinically suspected.",
                "Repeat inflammatory markers (CRP/WBC) in 48-72 hours to evaluate treatment response."
            ]
        elif "glucose" in text_lower or "diabetes" in text_lower or "hba1c" in text_lower:
            params = [
                {"name": "Fasting Blood Glucose", "value": "142", "unit": "mg/dL", "reference_range": "70 - 99", "status": "High", "critical": False},
                {"name": "HbA1c", "value": "7.6", "unit": "%", "reference_range": "< 5.7", "status": "High", "critical": False},
                {"name": "Total Cholesterol", "value": "218", "unit": "mg/dL", "reference_range": "< 200", "status": "High", "critical": False},
                {"name": "Triglycerides", "value": "185", "unit": "mg/dL", "reference_range": "< 150", "status": "High", "critical": False},
                {"name": "Serum Creatinine", "value": "0.95", "unit": "mg/dL", "reference_range": "0.7 - 1.3", "status": "Normal", "critical": False}
            ]
            abnormal = [
                "Elevated Fasting Glucose (142 mg/dL) and HbA1c (7.6%), consistent with suboptimally controlled hyperglycemia.",
                "Borderline elevated total cholesterol and triglycerides."
            ]
            interpretation = "Metabolic profile consistent with Type 2 Diabetes Mellitus with secondary dyslipidemia. Renal function markers (Creatinine) remain preserved."
            causes = ["Type 2 Diabetes Mellitus", "Metabolic Syndrome", "Insulin Resistance"]
            actions = [
                "Evaluate and initiate/adjust anti-diabetic oral regimen (e.g. Metformin titrated to tolerance).",
                "Recommend medical nutrition therapy, weight management, and aerobic exercise.",
                "Schedule repeat glycemic evaluation (HbA1c) in 3 months."
            ]
        else:
            params = [
                {"name": "Sodium (Na)", "value": "140", "unit": "mEq/L", "reference_range": "135 - 145", "status": "Normal", "critical": False},
                {"name": "Potassium (K)", "value": "4.2", "unit": "mEq/L", "reference_range": "3.5 - 5.0", "status": "Normal", "critical": False},
                {"name": "Blood Urea Nitrogen (BUN)", "value": "16", "unit": "mg/dL", "reference_range": "7 - 20", "status": "Normal", "critical": False},
                {"name": "Serum Creatinine", "value": "0.88", "unit": "mg/dL", "reference_range": "0.7 - 1.3", "status": "Normal", "critical": False},
                {"name": "eGFR", "value": "95", "unit": "mL/min/1.73m2", "reference_range": "> 60", "status": "Normal", "critical": False}
            ]
            abnormal = ["All evaluated primary biochemical parameters fall within established reference intervals."]
            interpretation = "Routine clinical chemistry panel demonstrates preserved renal and electrolyte homeostasis without acute derangements."
            causes = ["Physiologic baseline state", "Normal homeostatic parameters"]
            actions = [
                "Maintain standard preventive health surveillance.",
                "Follow up routinely as clinically warranted by patient's primary symptoms."
            ]

        return {
            "test_type": test_type,
            "parameters": params,
            "abnormal_findings_summary": abnormal,
            "primary_interpretation": interpretation,
            "potential_causes": causes,
            "clinical_action_items": actions,
            "safety_warning": DISCLAIMER
        }

    @staticmethod
    def _mock_clinical_assistant(vitals, chief_complaint, symptoms, medical_history, current_medications):
        comb_text = f"{chief_complaint} {symptoms} {medical_history}".lower()
        v = vitals or {}
        temp = v.get('temperature', 37.0)
        hr = v.get('pulse_rate', 75)
        spo2 = v.get('spo2', 98)
        
        if "chest" in comb_text and ("pain" in comb_text or "pressure" in comb_text or "tight" in comb_text):
            diagnoses = [
                {"diagnosis": "Gastroesophageal Reflux Disease (GERD) / Esophageal Spasm", "likelihood": "High", "rationale": "Substernal discomfort exacerbated in recumbent position, absence of acute diaphoresis."},
                {"diagnosis": "Costochondritis / Musculoskeletal Chest Wall Pain", "likelihood": "Moderate", "rationale": "Chest pain with localized tenderness on sternocostal junction palpation."},
                {"diagnosis": "Atypical Angina Pectoris", "likelihood": "Low-Moderate", "rationale": "Requires urgent exclusion of acute coronary syndrome via serial troponins and 12-lead ECG."}
            ]
            tests = ["12-Lead Electrocardiogram (ECG)", "Serial High-Sensitivity Troponin I", "Chest X-Ray (PA & Lateral)"]
            treatment = [
                {"medication": "Pantoprazole 40mg", "dosage": "1 Tablet", "frequency": "Once daily before breakfast", "duration": "14 Days", "warning": "Take on empty stomach 30 mins before food."},
                {"medication": "Antacid Susp (Mg/Al Hydroxide)", "dosage": "10 mL", "frequency": "Three times daily after meals", "duration": "7 Days", "warning": "Space 2 hours apart from other oral medications."}
            ]
            summary = "Patient presents with chest symptoms. Immediate priority is ruling out acute coronary syndrome with ECG and cardiac enzymes before confirming gastrointestinal or musculoskeletal etiology."
            
        elif "fever" in comb_text or "cough" in comb_text or "throat" in comb_text:
            diagnoses = [
                {"diagnosis": "Acute Upper Respiratory Tract Infection (URTI)", "likelihood": "High", "rationale": f"Fever ({temp}°C) and productive cough with normal oxygen saturation ({spo2}%)."},
                {"diagnosis": "Acute Bronchitis", "likelihood": "Moderate", "rationale": "Persistent bronchial irritation and rhonchi on auscultation."},
                {"diagnosis": "Seasonal Influenza / Viral Syndrome", "likelihood": "Moderate", "rationale": "Associated myalgia and systemic fatigue."}
            ]
            tests = ["Complete Blood Count (CBC)", "Rapid Influenza / Viral Antigen Panel", "Chest X-Ray if crackles or hypoxia present"]
            treatment = [
                {"medication": "Paracetamol 500mg", "dosage": "1-2 Tablets", "frequency": "Every 6-8 hours PRN for fever/pain", "duration": "5 Days", "warning": "Do not exceed 4,000 mg in 24 hours to prevent hepatotoxicity."},
                {"medication": "Cetirizine 10mg", "dosage": "1 Tablet", "frequency": "Once daily at bedtime", "duration": "5 Days", "warning": "May cause mild sedation; avoid alcohol."},
                {"medication": "Dextromethorphan Syrup", "dosage": "10 mL", "frequency": "Every 8 hours as needed", "duration": "5 Days", "warning": "Use for dry hacking cough; maintain oral hydration."}
            ]
            summary = f"Presentation consistent with acute viral respiratory illness. Vitals stable (HR: {hr} bpm, SpO2: {spo2}%). Supportive symptomatic management with clear red-flag precautions."
            
        elif "headache" in comb_text or "migraine" in comb_text:
            diagnoses = [
                {"diagnosis": "Episodic Tension-Type Headache", "likelihood": "High", "rationale": "Bilateral band-like pressure, exacerbated by stress/fatigue, no focal deficits."},
                {"diagnosis": "Common Migraine (without aura)", "likelihood": "Moderate", "rationale": "Throbbing quality, moderate intensity, potential photophobia."}
            ]
            tests = ["Fundoscopic examination", "Neurological examination documentation", "Blood pressure tracking"]
            treatment = [
                {"medication": "Ibuprofen 400mg", "dosage": "1 Tablet", "frequency": "Three times daily with food", "duration": "3 Days", "warning": "Always take with food; avoid in active peptic ulcer disease."},
                {"medication": "Paracetamol 500mg", "dosage": "2 Tablets", "frequency": "Every 8 hours as needed", "duration": "3 Days", "warning": "Avoid combination with other acetaminophen-containing cold medicines."}
            ]
            summary = "Acute cephalalgia presentation. Rule out secondary causes and manage with first-line analgesics and hydration."
            
        else:
            diagnoses = [
                {"diagnosis": "Acute Non-Specific Illness", "likelihood": "Moderate", "rationale": "Clinical picture requires correlation with detailed physical exam."},
                {"diagnosis": "Viral Syndrome", "likelihood": "Moderate", "rationale": "Constitutional symptoms present with preserved hemodynamic parameters."}
            ]
            tests = ["Routine Complete Blood Count (CBC)", "Basic Metabolic Panel (BMP)", "Urinalysis"]
            treatment = [
                {"medication": "Supportive Fluid & Electrolyte Therapy", "dosage": "Oral", "frequency": "Ad libitum", "duration": "Ongoing", "warning": "Ensure adequate fluid intake."},
                {"medication": "Paracetamol 500mg", "dosage": "1 Tablet", "frequency": "Every 8 hours PRN", "duration": "3 Days", "warning": "Max 4g daily."}
            ]
            summary = "Patient evaluated for general clinical complaints. Comprehensive baseline workup and symptom-directed therapy initiated."

        return {
            "potential_diagnoses": diagnoses,
            "recommended_tests": tests,
            "suggested_treatment_plan": treatment,
            "clinical_summary": summary,
            "safety_warning": DISCLAIMER
        }
