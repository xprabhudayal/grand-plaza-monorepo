"""
STT Evaluation Runner

Main script to run STT evaluations using predefined ground truth cases.
This script ties together the ground truth data, metrics, and provider evaluations.
"""

import asyncio
import json
import os
from typing import Dict, Any, List
import argparse
from datetime import datetime

from .ground_truth import GROUND_TRUTH_CASES, ScenarioType, get_cases_by_scenario
from .providers import STTEvaluator, create_provider_from_config
from .metrics import evaluate_transcript

class EvaluationRunner:
    """Main runner for STT evaluations"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.providers = self._initialize_providers()
        self.evaluator = STTEvaluator(self.providers) if self.providers else None
        self.results_dir = self.config.get('results_dir', 'evaluation_results')
        
        # Create results directory
        os.makedirs(self.results_dir, exist_ok=True)
    
    def _load_config(self, config_file: str = None) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration - you can modify these
        return {
            'audio_base_path': 'evaluation_audio/',  # Directory containing audio files
            'providers': {
                'soniox': {
                    'api_key': os.getenv('SONIOX_API_KEY', ''),
                    'model': 'en_v2_lowlatency'
                },
                'deepgram': {
                    'api_key': os.getenv('DEEPGRAM_API_KEY', ''),
                    'model': 'nova-2',
                    'language': 'en-US'
                },
                'assemblyai': {
                    'api_key': os.getenv('ASSEMBLYAI_API_KEY', ''),
                    'model': 'best'
                },
                'groq_whisper': {
                    'api_key': os.getenv('GROQ_API_KEY', ''),
                    'model': 'whisper-large-v3-turbo'
                }
            },
            'results_dir': 'evaluation_results',
            'enabled_providers': ['soniox', 'deepgram', 'assemblyai', 'groq_whisper']
        }
    
    def _initialize_providers(self) -> List:
        """Initialize enabled STT providers"""
        providers = []
        
        for provider_name in self.config.get('enabled_providers', []):
            if provider_name in self.config['providers']:
                provider_config = self.config['providers'][provider_name].copy()
                
                if not provider_config.get('api_key'):
                    print(f"Warning: No API key found for {provider_name}, skipping...")
                    continue
                
                try:
                    provider = create_provider_from_config(provider_name, provider_config)
                    if provider.validate_config():
                        providers.append(provider)
                        print(f"✓ Initialized {provider_name} provider")
                    else:
                        print(f"✗ Invalid configuration for {provider_name}")
                except Exception as e:
                    print(f"✗ Failed to initialize {provider_name}: {e}")
        
        return providers
    
    def get_audio_file_path(self, filename: str) -> str:
        """Get full path to audio file"""
        base_path = self.config.get('audio_base_path', 'evaluation_audio/')
        return os.path.join(base_path, filename)
    
    async def run_single_case_evaluation(self, case_id: str) -> Dict[str, Any]:
        """Run evaluation for a single test case"""
        if not self.evaluator:
            raise RuntimeError("No providers initialized")
        
        # Find the test case
        test_case = None
        for case in GROUND_TRUTH_CASES:
            if case.case_id == case_id:
                test_case = case
                break
        
        if not test_case:
            raise ValueError(f"Test case {case_id} not found")
        
        # Get audio file path
        audio_path = self.get_audio_file_path(test_case.audio_filename)
        
        # Check if audio file exists
        if not os.path.exists(audio_path):
            print(f"Warning: Audio file {audio_path} not found. Using placeholder path.")
        
        # Run evaluation
        result = await self.evaluator.evaluate_single_audio(audio_path, test_case.ground_truth)
        
        # Add test case metadata
        result['test_case'] = {
            'case_id': test_case.case_id,
            'scenario_type': test_case.scenario_type.value,
            'description': test_case.description,
            'expected_challenges': test_case.expected_challenges,
            'metadata': test_case.metadata
        }
        
        return result
    
    async def run_scenario_evaluation(self, scenario_type: ScenarioType) -> List[Dict[str, Any]]:
        """Run evaluation for all test cases in a scenario"""
        cases = get_cases_by_scenario(scenario_type)
        results = []
        
        for case in cases:
            try:
                result = await self.run_single_case_evaluation(case.case_id)
                results.append(result)
                print(f"✓ Completed evaluation for {case.case_id}")
            except Exception as e:
                print(f"✗ Failed evaluation for {case.case_id}: {e}")
                # Add error result
                results.append({
                    'test_case': {'case_id': case.case_id},
                    'error': str(e)
                })
        
        return results
    
    async def run_full_evaluation(self) -> Dict[str, Any]:
        """Run evaluation for all test cases"""
        if not self.evaluator:
            raise RuntimeError("No providers initialized")
        
        print("Starting full STT evaluation...")
        print(f"Total test cases: {len(GROUND_TRUTH_CASES)}")
        print(f"Providers: {[p.provider_name for p in self.providers]}")
        print("=" * 50)
        
        all_results = []
        
        # Group by scenario for organized execution
        for scenario_type in ScenarioType:
            cases = get_cases_by_scenario(scenario_type)
            if not cases:
                continue
            
            print(f"\nEvaluating {scenario_type.value} scenarios ({len(cases)} cases):")
            scenario_results = await self.run_scenario_evaluation(scenario_type)
            all_results.extend(scenario_results)
        
        # Generate comparison report
        comparison_report = self.evaluator.generate_comparison_report(
            [r for r in all_results if 'error' not in r]
        )
        
        return {
            'evaluation_timestamp': datetime.now().isoformat(),
            'configuration': {
                'providers': [p.provider_name for p in self.providers],
                'total_cases': len(GROUND_TRUTH_CASES),
                'successful_cases': len([r for r in all_results if 'error' not in r])
            },
            'individual_results': all_results,
            'comparison_report': comparison_report
        }
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save evaluation results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stt_evaluation_{timestamp}.json"
        
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results saved to: {filepath}")
        return filepath
    
    def print_summary(self, results: Dict[str, Any]):
        """Print evaluation summary"""
        comparison = results.get('comparison_report', {})
        summary = comparison.get('summary', {})
        
        print("\n" + "=" * 60)
        print("STT EVALUATION SUMMARY")
        print("=" * 60)
        
        if not summary:
            print("No results to summarize")
            return
        
        print(f"Total test cases: {comparison.get('total_test_cases', 0)}")
        print(f"Providers evaluated: {len(summary)}")
        print()
        
        # Sort providers by mean WER (lower is better)
        sorted_providers = sorted(
            summary.items(), 
            key=lambda x: x[1].get('mean_wer', float('inf'))
        )
        
        print("Provider Performance (sorted by WER):")
        print("-" * 50)
        print(f"{'Provider':<15} {'WER':<8} {'CER':<8} {'Accuracy':<10} {'Success%':<10}")
        print("-" * 50)
        
        for provider_name, metrics in sorted_providers:
            wer = metrics.get('mean_wer', 0)
            cer = metrics.get('mean_cer', 0)
            accuracy = metrics.get('mean_word_accuracy', 0)
            success_rate = metrics.get('success_rate', 0)
            
            print(f"{provider_name:<15} {wer:<8.3f} {cer:<8.3f} {accuracy:<10.3f} {success_rate*100:<10.1f}")
        
        print("\nMetric Definitions:")
        print("- WER: Word Error Rate (lower is better)")
        print("- CER: Character Error Rate (lower is better)")  
        print("- Accuracy: Word-level accuracy (higher is better)")
        print("- Success%: Percentage of successful transcriptions")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='STT Evaluation Runner')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--case-id', type=str, help='Run single test case')
    parser.add_argument('--scenario', type=str, help='Run specific scenario')
    parser.add_argument('--list-cases', action='store_true', help='List all test cases')
    parser.add_argument('--list-scenarios', action='store_true', help='List all scenarios')
    parser.add_argument('--output', type=str, help='Output file name')
    
    args = parser.parse_args()
    
    if args.list_cases:
        print("Available Test Cases:")
        print("-" * 40)
        for case in GROUND_TRUTH_CASES:
            print(f"{case.case_id:<15} {case.scenario_type.value:<20} {case.description}")
        return
    
    if args.list_scenarios:
        print("Available Scenarios:")
        print("-" * 30)
        for scenario in ScenarioType:
            cases = get_cases_by_scenario(scenario)
            print(f"{scenario.value:<25} ({len(cases)} cases)")
        return
    
    # Initialize runner
    runner = EvaluationRunner(args.config)
    
    if not runner.providers:
        print("No providers configured. Please check your API keys and configuration.")
        return
    
    # Run evaluation
    async def run_evaluation():
        if args.case_id:
            # Single case
            result = await runner.run_single_case_evaluation(args.case_id)
            results = {
                'evaluation_timestamp': datetime.now().isoformat(),
                'single_case_result': result
            }
        elif args.scenario:
            # Scenario
            scenario_type = None
            for st in ScenarioType:
                if st.value == args.scenario:
                    scenario_type = st
                    break
            
            if not scenario_type:
                print(f"Unknown scenario: {args.scenario}")
                return
            
            scenario_results = await runner.run_scenario_evaluation(scenario_type)
            results = {
                'evaluation_timestamp': datetime.now().isoformat(),
                'scenario': args.scenario,
                'scenario_results': scenario_results
            }
        else:
            # Full evaluation
            results = await runner.run_full_evaluation()
        
        # Save and display results
        output_file = runner.save_results(results, args.output)
        runner.print_summary(results)
        
        return results
    
    # Run the async evaluation
    asyncio.run(run_evaluation())

if __name__ == "__main__":
    main()