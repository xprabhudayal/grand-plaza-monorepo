# STT Evaluation Framework

A comprehensive framework for evaluating Speech-to-Text (STT) accuracy across multiple providers including Soniox, Deepgram, AssemblyAI, and OpenAI Whisper (via Groq).

## Features

- **Multiple Evaluation Metrics**:
  - Word Error Rate (WER) - Traditional word-level accuracy
  - Character Error Rate (CER) - Character-level accuracy  
  - Semantic Similarity - Meaning preservation evaluation
  - SeMaScore - 2024 advanced metric combining error rate and semantic understanding

- **STT Provider Support**:
  - Soniox Speech-to-Text API
  - Deepgram Nova-2 and other models
  - AssemblyAI Universal models
  - OpenAI Whisper via Groq

- **Predefined Test Cases**: 25+ ground truth cases covering:
  - Clear speech scenarios
  - Accented speech variations
  - Technical terminology (programming, medical)
  - Numbers and date formats
  - Proper names and places
  - Hotel/hospitality context (tailored for your use case)
  - Emotional speech patterns
  - Noisy environments
  - Multiple speakers

## Setup

1. Install dependencies:
```bash
pip install -r evaluations/requirements.txt
```

2. Configure API keys (choose your preferred method):

**Option A: Environment variables**
```bash
export SONIOX_API_KEY="your_soniox_key"
export DEEPGRAM_API_KEY="your_deepgram_key" 
export ASSEMBLYAI_API_KEY="your_assemblyai_key"
export GROQ_API_KEY="your_groq_key"
```

**Option B: Configuration file**
Create `evaluation_config.json`:
```json
{
  "providers": {
    "soniox": {"api_key": "your_key", "model": "en_v2_lowlatency"},
    "deepgram": {"api_key": "your_key", "model": "nova-2"}, 
    "assemblyai": {"api_key": "your_key"},
    "groq_whisper": {"api_key": "your_key", "model": "whisper-large-v3-turbo"}
  },
  "audio_base_path": "evaluation_audio/",
  "enabled_providers": ["deepgram", "assemblyai", "groq_whisper"]
}
```

3. Add your audio files to `evaluation_audio/` directory following the naming convention in ground_truth.py

## Usage

### List Available Test Cases
```bash
cd evaluations
python runner.py --list-cases
```

### List Available Scenarios  
```bash
python runner.py --list-scenarios
```

### Run Full Evaluation
```bash
python runner.py --output my_evaluation.json
```

### Run Specific Scenario
```bash
python runner.py --scenario hotel_context
```

### Run Single Test Case
```bash
python runner.py --case-id clear_001
```

### Using Custom Config
```bash
python runner.py --config my_config.json
```

## File Structure

```
evaluations/
├── __init__.py              # Package initialization
├── ground_truth.py          # Predefined test cases and ground truths
├── metrics.py               # WER, CER, semantic similarity calculations  
├── providers.py             # STT provider implementations
├── runner.py                # Main evaluation runner and CLI
├── requirements.txt         # Dependencies
└── README.md               # This file

evaluation_audio/           # Audio files directory (you create this)
├── clear_speech_hello.wav
├── tech_terms_api.wav
├── hotel_reservation.wav
└── ...

evaluation_results/         # Results output directory  
├── stt_evaluation_20250120_143022.json
└── ...
```

## Ground Truth Test Cases

The framework includes 25+ predefined test cases across various scenarios:

### Clear Speech (2 cases)
- Basic greetings
- Weather descriptions with numbers

### Technical Terms (2 cases)  
- Programming/API terminology
- Medical terminology

### Numbers & Dates (2 cases)
- Phone number dictation
- Meeting scheduling

### Proper Names (2 cases)
- International names with titles
- Geographic locations

### Hotel Context (3 cases) 
- Reservation requests
- Room service orders  
- Concierge services

### Additional Scenarios
- Accented speech (British, Indian English)
- Fast speech patterns
- Multiple speakers
- Emotional speech (excited, frustrated)
- Noisy environments

## Evaluation Metrics

### Traditional Metrics
- **WER (Word Error Rate)**: (Substitutions + Deletions + Insertions) / Total Words
- **CER (Character Error Rate)**: Character-level accuracy

### Advanced Metrics  
- **Semantic Similarity**: Meaning preservation using word overlap (extensible to BERT)
- **SeMaScore**: α × (1 - WER) + (1 - α) × Semantic_Similarity

### Output Includes
- Individual transcription results
- Confidence scores per provider
- Processing times
- Error analysis (insertions, deletions, substitutions)
- Aggregate statistics across all test cases

## Example Output

```
STT EVALUATION SUMMARY
============================================================
Total test cases: 25
Providers evaluated: 3

Provider Performance (sorted by WER):
--------------------------------------------------
Provider        WER      CER      Accuracy   Success%  
--------------------------------------------------
assemblyai      0.127    0.089    0.873      100.0    
deepgram        0.156    0.112    0.844      100.0    
groq_whisper    0.189    0.134    0.811      96.0     
```

## Extending the Framework

### Adding New Test Cases
Edit `ground_truth.py` and add to `GROUND_TRUTH_CASES`:
```python
GroundTruthCase(
    case_id="custom_001",
    audio_filename="my_audio.wav", 
    ground_truth="Expected transcription text",
    scenario_type=ScenarioType.CLEAR_SPEECH,
    description="Description of test case",
    expected_challenges=["challenge1", "challenge2"],
    metadata={"speaker": "native_english", "duration_seconds": 4}
)
```

### Adding New Providers
1. Subclass `STTProvider` in `providers.py`
2. Implement `transcribe_audio()` and `validate_config()`  
3. Add to the provider factory in `create_provider_from_config()`

### Custom Metrics
Add new evaluation functions to `metrics.py` and update `evaluate_transcript()`.

## Audio File Requirements

- Place audio files in `evaluation_audio/` directory
- Use the exact filenames specified in ground truth cases
- Supported formats: WAV, MP3, FLAC (provider dependent)
- Recommended: 16kHz sample rate, mono channel

## Notes

- The framework uses placeholder implementations for actual STT API calls
- Replace placeholder code in `providers.py` with real SDK calls
- Each provider may have different audio format requirements
- Consider rate limiting when running full evaluations
- Results are saved as JSON for further analysis

## License

[Add your license information]