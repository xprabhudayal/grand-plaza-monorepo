"""
STT Evaluation Metrics

This module implements various metrics for evaluating Speech-to-Text accuracy:
- Word Error Rate (WER) - Traditional word-level accuracy metric
- Character Error Rate (CER) - Character-level accuracy metric  
- Semantic Similarity - BERT-based semantic understanding metric
- SeMaScore - 2024 advanced metric combining error rate with semantic similarity
"""

import re
import string
from typing import List, Tuple, Dict, Any
from difflib import SequenceMatcher
import numpy as np
from dataclasses import dataclass

@dataclass
class EvaluationResult:
    """Container for evaluation results"""
    wer: float
    cer: float
    semantic_similarity: float = None
    sema_score: float = None
    word_accuracy: float = None
    insertions: int = 0
    deletions: int = 0
    substitutions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wer': self.wer,
            'cer': self.cer, 
            'semantic_similarity': self.semantic_similarity,
            'sema_score': self.sema_score,
            'word_accuracy': self.word_accuracy,
            'insertions': self.insertions,
            'deletions': self.deletions,
            'substitutions': self.substitutions
        }

def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by:
    - Converting to lowercase
    - Removing punctuation
    - Removing extra whitespace
    - Expanding common contractions
    """
    # Convert to lowercase
    text = text.lower()
    
    # Expand contractions
    contractions = {
        "i'm": "i am", "you're": "you are", "he's": "he is", "she's": "she is",
        "it's": "it is", "we're": "we are", "they're": "they are",
        "i've": "i have", "you've": "you have", "we've": "we have", "they've": "they have",
        "i'll": "i will", "you'll": "you will", "he'll": "he will", "she'll": "she will",
        "we'll": "we will", "they'll": "they will",
        "won't": "will not", "can't": "cannot", "don't": "do not", "doesn't": "does not",
        "didn't": "did not", "isn't": "is not", "aren't": "are not", "wasn't": "was not",
        "weren't": "were not", "hasn't": "has not", "haven't": "have not",
        "hadn't": "had not", "shouldn't": "should not", "couldn't": "could not",
        "wouldn't": "would not", "mustn't": "must not", "needn't": "need not"
    }
    
    for contraction, expansion in contractions.items():
        text = re.sub(r'\b' + contraction + r'\b', expansion, text)
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def levenshtein_distance(seq1: List[str], seq2: List[str]) -> Tuple[int, int, int, int]:
    """
    Calculate Levenshtein distance and return edit operations count.
    Returns: (distance, insertions, deletions, substitutions)
    """
    len1, len2 = len(seq1), len(seq2)
    
    # Create distance matrix
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    # Initialize base cases
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    
    # Fill the matrix
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if seq1[i-1] == seq2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(
                    dp[i-1][j],    # deletion
                    dp[i][j-1],    # insertion  
                    dp[i-1][j-1]   # substitution
                )
    
    # Backtrack to count operations
    i, j = len1, len2
    insertions = deletions = substitutions = 0
    
    while i > 0 or j > 0:
        if i > 0 and j > 0 and seq1[i-1] == seq2[j-1]:
            # Match - no operation
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            # Substitution
            substitutions += 1
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
            # Deletion
            deletions += 1
            i -= 1
        elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
            # Insertion
            insertions += 1
            j -= 1
        else:
            break
    
    return dp[len1][len2], insertions, deletions, substitutions

def calculate_wer(reference: str, hypothesis: str) -> Tuple[float, int, int, int]:
    """
    Calculate Word Error Rate (WER)
    WER = (S + D + I) / N
    Where S=substitutions, D=deletions, I=insertions, N=total words in reference
    """
    # Normalize both texts
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)
    
    # Split into words
    ref_words = ref_normalized.split()
    hyp_words = hyp_normalized.split()
    
    # Calculate edit distance and operations
    distance, insertions, deletions, substitutions = levenshtein_distance(ref_words, hyp_words)
    
    # Calculate WER
    total_words = len(ref_words)
    if total_words == 0:
        return 0.0 if len(hyp_words) == 0 else float('inf'), insertions, deletions, substitutions
    
    wer = distance / total_words
    return wer, insertions, deletions, substitutions

def calculate_cer(reference: str, hypothesis: str) -> float:
    """
    Calculate Character Error Rate (CER)
    CER = (S + D + I) / N
    Where S=substitutions, D=deletions, I=insertions, N=total characters in reference
    """
    # Normalize both texts but keep spaces
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)
    
    # Convert to character lists
    ref_chars = list(ref_normalized)
    hyp_chars = list(hyp_normalized)
    
    # Calculate edit distance
    distance, _, _, _ = levenshtein_distance(ref_chars, hyp_chars)
    
    # Calculate CER
    total_chars = len(ref_chars)
    if total_chars == 0:
        return 0.0 if len(hyp_chars) == 0 else float('inf')
    
    return distance / total_chars

def calculate_semantic_similarity(reference: str, hypothesis: str) -> float:
    """
    Calculate semantic similarity using simple word overlap as baseline.
    In production, this should use BERT or similar embeddings.
    
    Note: This is a simplified implementation. For real evaluation,
    use sentence-transformers or similar libraries.
    """
    # Normalize texts
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)
    
    # Get unique words
    ref_words = set(ref_normalized.split())
    hyp_words = set(hyp_normalized.split())
    
    # Calculate Jaccard similarity as proxy for semantic similarity
    if len(ref_words) == 0 and len(hyp_words) == 0:
        return 1.0
    
    intersection = len(ref_words.intersection(hyp_words))
    union = len(ref_words.union(hyp_words))
    
    return intersection / union if union > 0 else 0.0

def calculate_sema_score(reference: str, hypothesis: str, alpha: float = 0.5) -> float:
    """
    Calculate SeMaScore (2024 metric combining WER and semantic similarity)
    SeMaScore = alpha * (1 - WER) + (1 - alpha) * semantic_similarity
    
    Args:
        reference: Ground truth text
        hypothesis: Predicted text
        alpha: Weight between error rate (alpha) and semantic similarity (1-alpha)
    """
    wer, _, _, _ = calculate_wer(reference, hypothesis)
    semantic_sim = calculate_semantic_similarity(reference, hypothesis)
    
    # Ensure WER is capped at 1.0 for SeMaScore calculation
    wer_capped = min(wer, 1.0)
    
    # SeMaScore combines word accuracy (1 - WER) and semantic similarity
    sema_score = alpha * (1 - wer_capped) + (1 - alpha) * semantic_sim
    
    return sema_score

def evaluate_transcript(reference: str, hypothesis: str) -> EvaluationResult:
    """
    Comprehensive evaluation of a transcript using multiple metrics
    """
    # Calculate WER and get operation counts
    wer, insertions, deletions, substitutions = calculate_wer(reference, hypothesis)
    
    # Calculate CER
    cer = calculate_cer(reference, hypothesis)
    
    # Calculate semantic similarity
    semantic_similarity = calculate_semantic_similarity(reference, hypothesis)
    
    # Calculate SeMaScore
    sema_score = calculate_sema_score(reference, hypothesis)
    
    # Calculate word accuracy (1 - WER, capped at 0)
    word_accuracy = max(0.0, 1.0 - wer)
    
    return EvaluationResult(
        wer=wer,
        cer=cer,
        semantic_similarity=semantic_similarity,
        sema_score=sema_score,
        word_accuracy=word_accuracy,
        insertions=insertions,
        deletions=deletions,
        substitutions=substitutions
    )

def batch_evaluate(reference_texts: List[str], hypothesis_texts: List[str]) -> List[EvaluationResult]:
    """
    Evaluate multiple transcript pairs
    """
    if len(reference_texts) != len(hypothesis_texts):
        raise ValueError("Reference and hypothesis lists must have the same length")
    
    results = []
    for ref, hyp in zip(reference_texts, hypothesis_texts):
        results.append(evaluate_transcript(ref, hyp))
    
    return results

def calculate_aggregate_metrics(results: List[EvaluationResult]) -> Dict[str, float]:
    """
    Calculate aggregate metrics across multiple evaluation results
    """
    if not results:
        return {}
    
    return {
        'mean_wer': np.mean([r.wer for r in results]),
        'median_wer': np.median([r.wer for r in results]),
        'mean_cer': np.mean([r.cer for r in results]),
        'median_cer': np.median([r.cer for r in results]),
        'mean_semantic_similarity': np.mean([r.semantic_similarity for r in results if r.semantic_similarity is not None]),
        'mean_sema_score': np.mean([r.sema_score for r in results if r.sema_score is not None]),
        'mean_word_accuracy': np.mean([r.word_accuracy for r in results if r.word_accuracy is not None]),
        'total_insertions': sum([r.insertions for r in results]),
        'total_deletions': sum([r.deletions for r in results]),
        'total_substitutions': sum([r.substitutions for r in results])
    }

# Example usage and testing
if __name__ == "__main__":
    # Test the metrics with sample data
    reference = "Hello, how are you doing today?"
    hypothesis_good = "Hello, how are you doing today?"
    hypothesis_bad = "Helo, how r u doing todya?"
    hypothesis_semantic = "Hi, how are you feeling today?"
    
    print("Testing STT Evaluation Metrics")
    print("=" * 50)
    
    # Perfect match
    result_perfect = evaluate_transcript(reference, hypothesis_good)
    print(f"Perfect match: WER={result_perfect.wer:.3f}, CER={result_perfect.cer:.3f}")
    
    # Spelling errors
    result_errors = evaluate_transcript(reference, hypothesis_bad)
    print(f"With errors: WER={result_errors.wer:.3f}, CER={result_errors.cer:.3f}")
    
    # Semantic preservation
    result_semantic = evaluate_transcript(reference, hypothesis_semantic)
    print(f"Semantic variant: WER={result_semantic.wer:.3f}, Semantic={result_semantic.semantic_similarity:.3f}, SeMaScore={result_semantic.sema_score:.3f}")