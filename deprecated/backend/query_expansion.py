"""
Query Expansion Module for Advanced RAG
Implements multiple query expansion strategies using Mistral embeddings
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from loguru import logger
from datetime import datetime
import re


@dataclass
class ExpansionResult:
    """Result of query expansion"""
    original_query: str
    expanded_terms: List[str]
    reformulated_queries: List[str]
    step_back_query: Optional[str] = None
    expansion_strategy: str = "basic"
    confidence_score: float = 0.0


class QueryExpander:
    """Advanced query expansion using Mistral embeddings and LLM"""
    
    def __init__(self, chroma_dir: str = "./chroma_db"):
        self.chroma_dir = chroma_dir
        self.embeddings = None
        self.llm = None
        self.menu_vectorstore = None
        
        # Expansion templates
        self.expansion_templates = {
            "menu_inquiry": [
                "What {item} options are available?",
                "Tell me about {item} on the menu",
                "Show me {item} dishes"
            ],
            "dietary_inquiry": [
                "What {dietary_type} options do you have?",
                "Which items are {dietary_type}?",
                "Do you have {dietary_type} dishes?"
            ],
            "ingredient_inquiry": [
                "What ingredients are in {item}?",
                "Does {item} contain {ingredient}?",
                "Is {item} made with {ingredient}?"
            ]
        }
        
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize Mistral embeddings and LLM"""
        try:
            api_key = os.getenv("MISTRAL_API_KEY")
            if not api_key:
                raise ValueError("MISTRAL_API_KEY not found in environment variables")
            
            self.embeddings = MistralAIEmbeddings(
                api_key=api_key,
                model="mistral-embed"
            )
            
            self.llm = ChatMistralAI(
                api_key=api_key,
                model="mistral-small-latest",
                temperature=0.3
            )
            
            # Initialize menu vectorstore for semantic similarity
            self.menu_vectorstore = Chroma(
                collection_name="hotel_menu",
                embedding_function=self.embeddings,
                persist_directory=self.chroma_dir
            )
            
            logger.info("Query expansion models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize query expansion models: {e}")
            raise
    
    def expand_query(self, query: str, retrieval_metadata: Optional[Dict[str, Any]] = None) -> ExpansionResult:
        """
        Expand query using multiple strategies based on intent and confidence
        
        Args:
            query: Original user query
            retrieval_metadata: Metadata from intent classification
            
        Returns:
            ExpansionResult with expanded terms and reformulated queries
        """
        try:
            if not retrieval_metadata:
                return self._basic_expansion(query)
            
            intent = retrieval_metadata.get("intent", "general_assistance")
            confidence = retrieval_metadata.get("confidence", 0.5)
            supports_expansion = retrieval_metadata.get("supports_expansion", False)
            supports_step_back = retrieval_metadata.get("supports_step_back", False)
            
            if not supports_expansion:
                return ExpansionResult(
                    original_query=query,
                    expanded_terms=[],
                    reformulated_queries=[query],
                    expansion_strategy="none"
                )
            
            # Choose expansion strategy based on intent and confidence
            if confidence > 0.8:
                return self._semantic_expansion(query, intent)
            elif confidence > 0.6:
                result = self._hybrid_expansion(query, intent)
                if supports_step_back:
                    result.step_back_query = self._generate_step_back_query(query, intent)
                return result
            else:
                return self._multi_strategy_expansion(query, intent)
                
        except Exception as e:
            logger.error(f"Error in query expansion: {e}")
            return ExpansionResult(
                original_query=query,
                expanded_terms=[],
                reformulated_queries=[query],
                expansion_strategy="fallback"
            )
    
    def _basic_expansion(self, query: str) -> ExpansionResult:
        """Basic expansion without intent information"""
        expanded_terms = self._extract_key_terms(query)
        
        return ExpansionResult(
            original_query=query,
            expanded_terms=expanded_terms,
            reformulated_queries=[query] + [f"{query} {term}" for term in expanded_terms[:2]],
            expansion_strategy="basic",
            confidence_score=0.5
        )
    
    def _semantic_expansion(self, query: str, intent: str) -> ExpansionResult:
        """High-confidence semantic expansion using embeddings"""
        try:
            # Get semantically similar menu items
            similar_docs = self.menu_vectorstore.similarity_search(query, k=5)
            expanded_terms = []
            
            for doc in similar_docs:
                # Extract relevant terms from similar documents
                terms = self._extract_menu_terms(doc.page_content)
                expanded_terms.extend(terms)
            
            # Remove duplicates and limit
            expanded_terms = list(set(expanded_terms))[:5]
            
            # Generate reformulated queries using templates
            reformulated = self._generate_template_queries(query, intent, expanded_terms)
            
            return ExpansionResult(
                original_query=query,
                expanded_terms=expanded_terms,
                reformulated_queries=[query] + reformulated,
                expansion_strategy="semantic",
                confidence_score=0.8
            )
            
        except Exception as e:
            logger.error(f"Error in semantic expansion: {e}")
            return self._basic_expansion(query)
    
    def _hybrid_expansion(self, query: str, intent: str) -> ExpansionResult:
        """Medium-confidence hybrid expansion combining multiple approaches"""
        try:
            # Combine semantic and template-based expansion
            semantic_result = self._semantic_expansion(query, intent)
            
            # Add LLM-generated reformulations
            llm_reformulations = self._llm_reformulate(query, intent)
            
            all_reformulated = list(set(semantic_result.reformulated_queries + llm_reformulations))
            
            return ExpansionResult(
                original_query=query,
                expanded_terms=semantic_result.expanded_terms,
                reformulated_queries=all_reformulated[:6],  # Limit to 6 variations
                expansion_strategy="hybrid",
                confidence_score=0.7
            )
            
        except Exception as e:
            logger.error(f"Error in hybrid expansion: {e}")
            return self._semantic_expansion(query, intent)
    
    def _multi_strategy_expansion(self, query: str, intent: str) -> ExpansionResult:
        """Low-confidence multi-strategy expansion for broader coverage"""
        try:
            # Use all available strategies
            expanded_terms = self._extract_key_terms(query)
            
            # Add semantic terms
            try:
                semantic_terms = self._get_semantic_neighbors(query)
                expanded_terms.extend(semantic_terms)
            except:
                pass
            
            # Generate multiple query variations
            reformulations = [query]
            
            # Template-based variations
            template_queries = self._generate_template_queries(query, intent, expanded_terms)
            reformulations.extend(template_queries)
            
            # Broader reformulations
            broader_queries = [
                f"Tell me about {query}",
                f"What information do you have about {query}",
                f"Help me understand {query}"
            ]
            reformulations.extend(broader_queries)
            
            return ExpansionResult(
                original_query=query,
                expanded_terms=list(set(expanded_terms))[:8],
                reformulated_queries=list(set(reformulations))[:8],
                expansion_strategy="multi_strategy",
                confidence_score=0.4
            )
            
        except Exception as e:
            logger.error(f"Error in multi-strategy expansion: {e}")
            return self._basic_expansion(query)
    
    def _generate_step_back_query(self, query: str, intent: str) -> str:
        """Generate a step-back query for conceptual understanding"""
        try:
            step_back_prompts = {
                "dietary_inquiry": f"What are the general dietary options and categories available?",
                "general_assistance": f"What are the main services and information available?",
                "menu_inquiry": f"What are the main menu categories and types of food available?",
                "ingredient_inquiry": f"What ingredients and allergen information is typically important for menu items?"
            }
            
            return step_back_prompts.get(intent, f"What general information is available about {query}?")
            
        except Exception as e:
            logger.error(f"Error generating step-back query: {e}")
            return f"What general information is available about {query}?"
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from query using simple NLP"""
        # Remove common stop words and extract meaningful terms
        stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'are', 'do', 'does', 'what', 'how', 'can', 'you', 'have'}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        return [word for word in words if word not in stop_words][:5]
    
    def _extract_menu_terms(self, content: str) -> List[str]:
        """Extract menu-specific terms from document content"""
        # Look for food items, categories, and descriptors
        food_terms = re.findall(r'\b(?:pizza|pasta|salad|sandwich|burger|soup|chicken|beef|fish|vegetarian|vegan|gluten.free)\b', content.lower())
        return list(set(food_terms))
    
    def _generate_template_queries(self, query: str, intent: str, terms: List[str]) -> List[str]:
        """Generate queries using predefined templates"""
        templates = self.expansion_templates.get(intent, [])
        reformulated = []
        
        for template in templates:
            for term in terms[:3]:  # Use top 3 terms
                try:
                    reformulated.append(template.format(item=term, dietary_type=term, ingredient=term))
                except:
                    continue
        
        return reformulated[:4]  # Limit to 4 template variations
    
    def _llm_reformulate(self, query: str, intent: str) -> List[str]:
        """Use LLM to generate reformulated queries"""
        try:
            prompt = f"""
            Given this user query about hotel menu/food service: "{query}"
            Intent category: {intent}
            
            Generate 2-3 alternative ways to ask the same question that might retrieve better information.
            Focus on being more specific or using different terminology.
            
            Return only the reformulated queries, one per line, without numbering or extra text.
            """
            
            response = self.llm.invoke(prompt)
            reformulations = [line.strip() for line in response.content.split('\n') if line.strip()]
            return reformulations[:3]
            
        except Exception as e:
            logger.error(f"Error in LLM reformulation: {e}")
            return []
    
    def _get_semantic_neighbors(self, query: str, k: int = 3) -> List[str]:
        """Get semantically similar terms using embeddings"""
        try:
            query_embedding = self.embeddings.embed_query(query)
            
            # Get similar documents and extract terms
            similar_docs = self.menu_vectorstore.similarity_search(query, k=k)
            neighbor_terms = []
            
            for doc in similar_docs:
                terms = self._extract_menu_terms(doc.page_content)
                neighbor_terms.extend(terms)
            
            return list(set(neighbor_terms))[:5]
            
        except Exception as e:
            logger.error(f"Error getting semantic neighbors: {e}")
            return []


# Global expander instance
_query_expander = None

def get_query_expander() -> QueryExpander:
    """Get or create the query expander singleton"""
    global _query_expander
    if _query_expander is None:
        _query_expander = QueryExpander()
    
    return _query_expander


def expand_user_query(query: str, retrieval_metadata: Optional[Dict[str, Any]] = None) -> ExpansionResult:
    """Convenience function for query expansion"""
    expander = get_query_expander()
    return expander.expand_query(query, retrieval_metadata)


# Test function
def test_query_expansion():
    """Test the query expansion module"""
    expander = get_query_expander()
    
    test_queries = [
        "what vegetarian options do you have",
        "pizza menu",
        "does the salad contain nuts",
        "I want to order food"
    ]
    
    print("Testing Query Expansion:")
    print("=" * 50)
    
    for query in test_queries:
        result = expander.expand_query(query)
        print(f"Original: {result.original_query}")
        print(f"Strategy: {result.expansion_strategy}")
        print(f"Expanded terms: {result.expanded_terms}")
        print(f"Reformulated: {result.reformulated_queries}")
        if result.step_back_query:
            print(f"Step-back: {result.step_back_query}")
        print("-" * 30)


if __name__ == "__main__":
    test_query_expansion()