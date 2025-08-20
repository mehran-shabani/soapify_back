"""
JSON Schema definition for SOAP structure.
"""

SOAP_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "title": "SOAP Note Schema",
    "description": "Structured format for medical SOAP notes",
    "properties": {
        "subjective": {
            "type": "object",
            "title": "Subjective (S)",
            "description": "Patient's description of symptoms and concerns",
            "properties": {
                "chief_complaint": {
                    "type": "string",
                    "title": "Chief Complaint",
                    "description": "Primary reason for visit",
                    "minLength": 1
                },
                "history_present_illness": {
                    "type": "string",
                    "title": "History of Present Illness",
                    "description": "Detailed description of current symptoms"
                },
                "review_of_systems": {
                    "type": "object",
                    "title": "Review of Systems",
                    "properties": {
                        "constitutional": {"type": "string"},
                        "cardiovascular": {"type": "string"},
                        "respiratory": {"type": "string"},
                        "gastrointestinal": {"type": "string"},
                        "genitourinary": {"type": "string"},
                        "musculoskeletal": {"type": "string"},
                        "neurological": {"type": "string"},
                        "psychiatric": {"type": "string"},
                        "endocrine": {"type": "string"},
                        "hematologic": {"type": "string"},
                        "allergic": {"type": "string"}
                    }
                },
                "past_medical_history": {
                    "type": "string",
                    "title": "Past Medical History"
                },
                "medications": {
                    "type": "array",
                    "title": "Current Medications",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "dosage": {"type": "string"},
                            "frequency": {"type": "string"},
                            "route": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                },
                "allergies": {
                    "type": "array",
                    "title": "Allergies",
                    "items": {
                        "type": "object",
                        "properties": {
                            "allergen": {"type": "string"},
                            "reaction": {"type": "string"},
                            "severity": {"type": "string", "enum": ["mild", "moderate", "severe"]}
                        },
                        "required": ["allergen"]
                    }
                },
                "social_history": {
                    "type": "object",
                    "title": "Social History",
                    "properties": {
                        "smoking": {"type": "string"},
                        "alcohol": {"type": "string"},
                        "drugs": {"type": "string"},
                        "occupation": {"type": "string"},
                        "family_history": {"type": "string"}
                    }
                }
            },
            "required": ["chief_complaint"]
        },
        "objective": {
            "type": "object",
            "title": "Objective (O)",
            "description": "Observable and measurable findings",
            "properties": {
                "vital_signs": {
                    "type": "object",
                    "title": "Vital Signs",
                    "properties": {
                        "temperature": {"type": "string"},
                        "blood_pressure": {"type": "string"},
                        "heart_rate": {"type": "string"},
                        "respiratory_rate": {"type": "string"},
                        "oxygen_saturation": {"type": "string"},
                        "weight": {"type": "string"},
                        "height": {"type": "string"},
                        "bmi": {"type": "string"}
                    }
                },
                "physical_examination": {
                    "type": "object",
                    "title": "Physical Examination",
                    "properties": {
                        "general_appearance": {"type": "string"},
                        "head_neck": {"type": "string"},
                        "cardiovascular": {"type": "string"},
                        "respiratory": {"type": "string"},
                        "abdominal": {"type": "string"},
                        "musculoskeletal": {"type": "string"},
                        "neurological": {"type": "string"},
                        "skin": {"type": "string"},
                        "psychiatric": {"type": "string"}
                    }
                },
                "laboratory_results": {
                    "type": "array",
                    "title": "Laboratory Results",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_name": {"type": "string"},
                            "result": {"type": "string"},
                            "reference_range": {"type": "string"},
                            "date": {"type": "string", "format": "date"}
                        },
                        "required": ["test_name", "result"]
                    }
                },
                "imaging_results": {
                    "type": "array",
                    "title": "Imaging Results",
                    "items": {
                        "type": "object",
                        "properties": {
                            "study_type": {"type": "string"},
                            "findings": {"type": "string"},
                            "impression": {"type": "string"},
                            "date": {"type": "string", "format": "date"}
                        },
                        "required": ["study_type"]
                    }
                }
            }
        },
        "assessment": {
            "type": "object",
            "title": "Assessment (A)",
            "description": "Clinical reasoning and diagnosis",
            "properties": {
                "primary_diagnosis": {
                    "type": "string",
                    "title": "Primary Diagnosis",
                    "description": "Main diagnosis with ICD-10 code if available",
                    "minLength": 1
                },
                "differential_diagnoses": {
                    "type": "array",
                    "title": "Differential Diagnoses",
                    "items": {
                        "type": "object",
                        "properties": {
                            "diagnosis": {"type": "string"},
                            "probability": {"type": "string"},
                            "reasoning": {"type": "string"}
                        },
                        "required": ["diagnosis"]
                    }
                },
                "clinical_reasoning": {
                    "type": "string",
                    "title": "Clinical Reasoning",
                    "description": "Thought process and rationale"
                },
                "severity": {
                    "type": "string",
                    "title": "Condition Severity",
                    "enum": ["mild", "moderate", "severe", "critical"]
                },
                "prognosis": {
                    "type": "string",
                    "title": "Prognosis",
                    "description": "Expected outcome and timeline"
                }
            },
            "required": ["primary_diagnosis"]
        },
        "plan": {
            "type": "object",
            "title": "Plan (P)",
            "description": "Treatment and follow-up plan",
            "properties": {
                "treatment_plan": {
                    "type": "object",
                    "title": "Treatment Plan",
                    "properties": {
                        "medications": {
                            "type": "array",
                            "title": "Prescribed Medications",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "medication": {"type": "string"},
                                    "dosage": {"type": "string"},
                                    "frequency": {"type": "string"},
                                    "duration": {"type": "string"},
                                    "instructions": {"type": "string"}
                                },
                                "required": ["medication", "dosage", "frequency"]
                            }
                        },
                        "procedures": {
                            "type": "array",
                            "title": "Planned Procedures",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "procedure": {"type": "string"},
                                    "indication": {"type": "string"},
                                    "timeline": {"type": "string"}
                                },
                                "required": ["procedure"]
                            }
                        },
                        "lifestyle_modifications": {
                            "type": "string",
                            "title": "Lifestyle Modifications"
                        }
                    }
                },
                "follow_up": {
                    "type": "object",
                    "title": "Follow-up Plan",
                    "properties": {
                        "next_appointment": {"type": "string"},
                        "monitoring": {"type": "string"},
                        "red_flags": {"type": "string"},
                        "patient_education": {"type": "string"}
                    }
                },
                "referrals": {
                    "type": "array",
                    "title": "Referrals",
                    "items": {
                        "type": "object",
                        "properties": {
                            "specialty": {"type": "string"},
                            "reason": {"type": "string"},
                            "urgency": {"type": "string", "enum": ["routine", "urgent", "emergent"]}
                        },
                        "required": ["specialty", "reason"]
                    }
                }
            }
        },
        "metadata": {
            "type": "object",
            "title": "Metadata",
            "properties": {
                "encounter_date": {"type": "string", "format": "date-time"},
                "doctor_name": {"type": "string"},
                "patient_ref": {"type": "string"},
                "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                "extraction_version": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"}
            },
            "required": ["encounter_date", "patient_ref"]
        }
    },
    "required": ["subjective", "objective", "assessment", "plan", "metadata"]
}

# Checklist items for comprehensive SOAP validation
SOAP_CHECKLIST_ITEMS = [
    {
        "id": "chief_complaint",
        "section": "subjective",
        "title": "Chief Complaint",
        "description": "Primary reason for patient visit",
        "required": True,
        "weight": 10
    },
    {
        "id": "history_present_illness",
        "section": "subjective", 
        "title": "History of Present Illness",
        "description": "Detailed symptom timeline and characteristics",
        "required": True,
        "weight": 8
    },
    {
        "id": "vital_signs",
        "section": "objective",
        "title": "Vital Signs",
        "description": "Temperature, BP, HR, RR, SpO2",
        "required": True,
        "weight": 7
    },
    {
        "id": "physical_exam",
        "section": "objective",
        "title": "Physical Examination",
        "description": "Systematic physical assessment",
        "required": True,
        "weight": 9
    },
    {
        "id": "primary_diagnosis",
        "section": "assessment",
        "title": "Primary Diagnosis",
        "description": "Main clinical diagnosis",
        "required": True,
        "weight": 10
    },
    {
        "id": "treatment_plan",
        "section": "plan",
        "title": "Treatment Plan",
        "description": "Medications, procedures, interventions",
        "required": True,
        "weight": 9
    },
    {
        "id": "follow_up",
        "section": "plan",
        "title": "Follow-up Plan",
        "description": "Next steps and monitoring",
        "required": True,
        "weight": 6
    },
    {
        "id": "allergies",
        "section": "subjective",
        "title": "Allergies",
        "description": "Known allergies and adverse reactions",
        "required": False,
        "weight": 5
    },
    {
        "id": "medications",
        "section": "subjective",
        "title": "Current Medications",
        "description": "Patient's current medication list",
        "required": False,
        "weight": 4
    },
    {
        "id": "social_history",
        "section": "subjective",
        "title": "Social History",
        "description": "Smoking, alcohol, occupation, family history",
        "required": False,
        "weight": 3
    }
]
