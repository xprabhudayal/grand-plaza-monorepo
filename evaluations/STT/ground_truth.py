"""
Ground Truth Test Cases for STT Evaluation

This module contains predefined ground truth transcriptions for various speech scenarios.
These will be used to evaluate the accuracy of different STT providers:
- Soniox
- Deepgram  
- AssemblyAI
- OpenAI Whisper (via Groq)
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

class ScenarioType(Enum):
    CLEAR_SPEECH = "clear_speech"
    ACCENTED_SPEECH = "accented_speech"
    NOISY_BACKGROUND = "noisy_background"
    TECHNICAL_TERMS = "technical_terms"
    NUMBERS_DATES = "numbers_dates"
    PROPER_NAMES = "proper_names"
    FAST_SPEECH = "fast_speech"
    MULTIPLE_SPEAKERS = "multiple_speakers"
    EMOTIONAL_SPEECH = "emotional_speech"
    HOTEL_CONTEXT = "hotel_context"

@dataclass
class GroundTruthCase:
    """Represents a single test case with ground truth transcription"""
    case_id: str
    audio_filename: str  # Expected audio file name
    ground_truth: str
    scenario_type: ScenarioType
    description: str
    expected_challenges: List[str]
    metadata: Dict[str, any]

# Ground Truth Test Cases
GROUND_TRUTH_CASES = [
    # Clear Speech Cases
    GroundTruthCase(
        case_id="clear_001",
        audio_filename="clear_speech_hello.wav",
        ground_truth="Hello, how are you doing today?",
        scenario_type=ScenarioType.CLEAR_SPEECH,
        description="Basic greeting with clear pronunciation",
        expected_challenges=[],
        metadata={"speaker": "native_english", "duration_seconds": 3}
    ),
    
    GroundTruthCase(
        case_id="clear_002", 
        audio_filename="clear_speech_weather.wav",
        ground_truth="The weather is beautiful today. It's sunny with a temperature of seventy-five degrees.",
        scenario_type=ScenarioType.CLEAR_SPEECH,
        description="Weather description with numbers",
        expected_challenges=["number_transcription"],
        metadata={"speaker": "native_english", "duration_seconds": 6}
    ),
    
    # Technical Terms
    GroundTruthCase(
        case_id="tech_001",
        audio_filename="tech_terms_api.wav", 
        ground_truth="I need to configure the REST API endpoint with JSON authentication tokens.",
        scenario_type=ScenarioType.TECHNICAL_TERMS,
        description="Technical programming terminology",
        expected_challenges=["technical_acronyms", "proper_case_sensitivity"],
        metadata={"speaker": "software_developer", "duration_seconds": 5}
    ),
    
    GroundTruthCase(
        case_id="tech_002",
        audio_filename="tech_terms_medical.wav",
        ground_truth="The patient has hypertension and requires antihypertensive medication.",
        scenario_type=ScenarioType.TECHNICAL_TERMS, 
        description="Medical terminology",
        expected_challenges=["medical_terms", "pronunciation_variants"],
        metadata={"speaker": "medical_professional", "duration_seconds": 4}
    ),
    
    # Numbers and Dates
    GroundTruthCase(
        case_id="numbers_001",
        audio_filename="numbers_phone.wav",
        ground_truth="Please call me at five five five, one two three, four five six seven.",
        scenario_type=ScenarioType.NUMBERS_DATES,
        description="Phone number dictation",
        expected_challenges=["number_formatting", "digit_vs_word_choice"],
        metadata={"speaker": "business_context", "duration_seconds": 5}
    ),
    
    GroundTruthCase(
        case_id="numbers_002",
        audio_filename="numbers_date.wav", 
        ground_truth="The meeting is scheduled for March fifteenth, twenty twenty-five at two thirty PM.",
        scenario_type=ScenarioType.NUMBERS_DATES,
        description="Date and time with mixed format",
        expected_challenges=["date_formatting", "time_representation", "am_pm_detection"],
        metadata={"speaker": "office_worker", "duration_seconds": 6}
    ),
    
    # Proper Names
    GroundTruthCase(
        case_id="names_001",
        audio_filename="names_international.wav",
        ground_truth="I'd like to speak with Dr. Rajesh Patel or Ms. Chen Wei about the appointment.",
        scenario_type=ScenarioType.PROPER_NAMES,
        description="International names with titles",
        expected_challenges=["name_spelling", "cultural_pronunciations", "title_recognition"],
        metadata={"speaker": "receptionist", "duration_seconds": 5}
    ),
    
    GroundTruthCase(
        case_id="names_002",
        audio_filename="names_places.wav",
        ground_truth="The package needs to be delivered to New York City, specifically to Brooklyn Heights.",
        scenario_type=ScenarioType.PROPER_NAMES,
        description="Geographic locations and places", 
        expected_challenges=["place_name_accuracy", "geographic_context"],
        metadata={"speaker": "logistics_coordinator", "duration_seconds": 4}
    ),
    
    # Hotel Context (Specific to your use case)
    GroundTruthCase(
        case_id="hotel_001",
        audio_filename="hotel_reservation.wav",
        ground_truth="I'd like to make a reservation for two guests from December tenth to December twelfth.",
        scenario_type=ScenarioType.HOTEL_CONTEXT,
        description="Hotel reservation request",
        expected_challenges=["date_parsing", "guest_count", "hospitality_terminology"],
        metadata={"speaker": "hotel_guest", "duration_seconds": 5}
    ),
    
    GroundTruthCase(
        case_id="hotel_002",
        audio_filename="hotel_room_service.wav",
        ground_truth="Could you please send room service to room four twenty-seven? I'd like to order a Caesar salad and a bottle of Pinot Grigio.",
        scenario_type=ScenarioType.HOTEL_CONTEXT,
        description="Room service order",
        expected_challenges=["room_number_format", "food_items", "wine_names"],
        metadata={"speaker": "hotel_guest", "duration_seconds": 8}
    ),
    
    GroundTruthCase(
        case_id="hotel_003",
        audio_filename="hotel_concierge.wav",
        ground_truth="Can the concierge help me book tickets for the Broadway show Hamilton tomorrow evening?",
        scenario_type=ScenarioType.HOTEL_CONTEXT,
        description="Concierge service request",
        expected_challenges=["service_terminology", "proper_names", "entertainment_context"],
        metadata={"speaker": "hotel_guest", "duration_seconds": 6}
    ),
    
    # Accented Speech
    GroundTruthCase(
        case_id="accent_001",
        audio_filename="accent_british.wav",
        ground_truth="I'm terribly sorry, but I can't find my lift key anywhere in my flat.",
        scenario_type=ScenarioType.ACCENTED_SPEECH,
        description="British English with regional vocabulary",
        expected_challenges=["accent_recognition", "regional_vocabulary", "pronunciation_variants"],
        metadata={"speaker": "british_english", "duration_seconds": 4}
    ),
    
    GroundTruthCase(
        case_id="accent_002",
        audio_filename="accent_indian.wav",
        ground_truth="Please schedule the meeting for tomorrow morning and send the agenda to all participants.",
        scenario_type=ScenarioType.ACCENTED_SPEECH,
        description="Indian English accent",
        expected_challenges=["accent_recognition", "pronunciation_patterns"],
        metadata={"speaker": "indian_english", "duration_seconds": 5}
    ),
    
    # Fast Speech
    GroundTruthCase(
        case_id="fast_001",
        audio_filename="fast_speech_directions.wav",
        ground_truth="Take the first left, then go straight for about two miles, and you'll see the building on your right after the traffic light.",
        scenario_type=ScenarioType.FAST_SPEECH,
        description="Rapid directions with spatial terms",
        expected_challenges=["speech_rate", "directional_terms", "distance_measures"],
        metadata={"speaker": "local_resident", "duration_seconds": 6, "speech_rate": "fast"}
    ),
    
    # Multiple Speakers
    GroundTruthCase(
        case_id="multi_001",
        audio_filename="multi_speakers_meeting.wav",
        ground_truth="Speaker A: Let's discuss the quarterly results. Speaker B: The revenue increased by fifteen percent. Speaker A: That's excellent news.",
        scenario_type=ScenarioType.MULTIPLE_SPEAKERS,
        description="Two speakers in business meeting",
        expected_challenges=["speaker_diarization", "context_switching", "overlapping_speech"],
        metadata={"speakers": 2, "context": "business_meeting", "duration_seconds": 8}
    ),
    
    # Emotional Speech
    GroundTruthCase(
        case_id="emotion_001",
        audio_filename="emotion_excited.wav",
        ground_truth="Oh my goodness, this is absolutely incredible! I can't believe how amazing this experience has been!",
        scenario_type=ScenarioType.EMOTIONAL_SPEECH,
        description="Excited, high-energy speech",
        expected_challenges=["emotional_prosody", "exclamations", "speech_dynamics"],
        metadata={"emotion": "excitement", "energy_level": "high", "duration_seconds": 5}
    ),
    
    GroundTruthCase(
        case_id="emotion_002", 
        audio_filename="emotion_frustrated.wav",
        ground_truth="I'm really frustrated with this situation. This is the third time I've had to call about the same issue.",
        scenario_type=ScenarioType.EMOTIONAL_SPEECH,
        description="Frustrated, complaint speech",
        expected_challenges=["emotional_stress", "complaint_context", "repetition_emphasis"],
        metadata={"emotion": "frustration", "context": "customer_service", "duration_seconds": 6}
    ),
    
    # Noisy Background
    GroundTruthCase(
        case_id="noisy_001",
        audio_filename="noisy_restaurant.wav",
        ground_truth="I'll have the grilled salmon with vegetables and a glass of white wine, please.",
        scenario_type=ScenarioType.NOISY_BACKGROUND,
        description="Restaurant order with background noise",
        expected_challenges=["background_noise", "food_terminology", "service_context"],
        metadata={"background": "restaurant_ambiance", "noise_level": "moderate", "duration_seconds": 5}
    ),
]

def get_cases_by_scenario(scenario_type: ScenarioType) -> List[GroundTruthCase]:
    """Filter test cases by scenario type"""
    return [case for case in GROUND_TRUTH_CASES if case.scenario_type == scenario_type]

def get_case_by_id(case_id: str) -> GroundTruthCase:
    """Get a specific test case by ID"""
    for case in GROUND_TRUTH_CASES:
        if case.case_id == case_id:
            return case
    raise ValueError(f"Case with ID {case_id} not found")

def get_all_case_ids() -> List[str]:
    """Get all available test case IDs"""
    return [case.case_id for case in GROUND_TRUTH_CASES]

def get_scenario_statistics() -> Dict[ScenarioType, int]:
    """Get count of test cases per scenario type"""
    stats = {}
    for scenario in ScenarioType:
        stats[scenario] = len(get_cases_by_scenario(scenario))
    return stats