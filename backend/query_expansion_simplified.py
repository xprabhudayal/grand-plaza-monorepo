"""
Simplified Query Expansion Module
Reduces complexity and uses unified configuration
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain_mistralai import ChatMistralAI
import re
from loguru import logger

from rag_config import get_rag_config
from chroma_manager import get_collection


@dataclass
class ExpansionResult:
    """Simplified expansion result"""
    original_query: str
    expanded_terms: List[str]
    reformulated_queries: List[str]
    expansion_strategy: str = "basic"


class SimplifiedQueryExpander:
    """Simplified query expansion with configuration-driven parameters"""
    
    def __init__(self, config=None):
        self.config = config or get_rag_config()
        self.llm = None
        self._vectorstore = None
        
        # Initialize LLM if available
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize Mistral LLM for query reformulation"""
        try:
            api_key = os.getenv("MISTRAL_API_KEY")
            if api_key:
                self.llm = ChatMistralAI(
                    api_key=api_key,
                    model="mistral-small-latest",
                    temperature=0.3
                )
                logger.info("Initialized Mistral LLM for query expansion")
        except Exception as e:
            logger.warning(f"Could not initialize LLM for expansion: {e}")
            self.llm = None
    
    def _get_vectorstore(self):
        """Get vectorstore for semantic expansion"""
        if self._vectorstore is None:
            try:
                self._vectorstore = get_collection("hotel_menu")
            except Exception as e:
                logger.warning(f"Could not get vectorstore for expansion: {e}")
                self._vectorstore = None
        return self._vectorstore
    
    def expand_query(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> ExpansionResult:
        """
        Expand query using simplified strategy selection
        
        Args:
            query: Original user query
            metadata: Optional metadata from intent classification
            
        Returns:
            ExpansionResult with expanded terms and reformulated queries
        """
        if not query or not query.strip():
            return ExpansionResult(query, [], [query], "empty")
        
        try:
            confidence = metadata.get("confidence", 0.5) if metadata else 0.5
            
            # Choose expansion strategy based on confidence
            if confidence >= self.config.intent_high_confidence:
                return self._semantic_expansion(query)
            elif confidence >= self.config.intent_medium_confidence:
                return self._hybrid_expansion(query)
            else:
                return self._basic_expansion(query)
                
        except Exception as e:
            logger.error(f"Error in query expansion: {e}")
            return ExpansionResult(query, [], [query], "error")
    
    def _semantic_expansion(self, query: str) -> ExpansionResult:
        """High confidence: Use semantic similarity"""
        expanded_terms = self._extract_key_terms(query)
        
        # Try semantic expansion with vectorstore
        vectorstore = self._get_vectorstore()
        if vectorstore:
            try:
                similar_docs = vectorstore.similarity_search(
                    query, 
                    k=self.config.query_expansion_semantic_k
                )
                
                for doc in similar_docs:
                    terms = self._extract_menu_terms(doc.page_content)
                    expanded_terms.extend(terms)
                
                # Remove duplicates and limit
                expanded_terms = list(set(expanded_terms))[:self.config.query_expansion_max_terms]
                
            except Exception as e:
                logger.warning(f"Semantic expansion failed: {e}")
        
        # Generate reformulated queries
        reformulated = self._generate_reformulations(query, expanded_terms)
        
        return ExpansionResult(
            original_query=query,
            expanded_terms=expanded_terms,
            reformulated_queries=[query] + reformulated,
            expansion_strategy="semantic"
        )
    
    def _hybrid_expansion(self, query: str) -> ExpansionResult:
        """Medium confidence: Combine semantic + LLM"""
        expanded_terms = self._extract_key_terms(query)
        reformulated = []
        
        # Try LLM reformulation
        if self.llm:
            try:
                llm_reformulations = self._llm_reformulate(query)
                reformulated.extend(llm_reformulations)
            except Exception as e:
                logger.warning(f"LLM reformulation failed: {e}")
        
        # Add template-based reformulations
        template_reformulations = self._template_reformulate(query, expanded_terms)
        reformulated.extend(template_reformulations)
        
        # Limit reformulations
        reformulated = list(set(reformulated))[:self.config.query_expansion_max_reformulations]
        
        return ExpansionResult(
            original_query=query,
            expanded_terms=expanded_terms,
            reformulated_queries=[query] + reformulated,
            expansion_strategy="hybrid"
        )
    
    def _basic_expansion(self, query: str) -> ExpansionResult:
        """Low confidence: Basic term extraction and templates"""
        expanded_terms = self._extract_key_terms(query)
        
        # Simple template-based reformulations
        reformulated = [
            f"Tell me about {query}",
            f"What information do you have about {query}",
            f"Help me understand {query}"
        ]
        
        # Limit results
        reformulated = reformulated[:self.config.query_expansion_max_reformulations]
        
        return ExpansionResult(
            original_query=query,
            expanded_terms=expanded_terms[:self.config.query_expansion_max_terms],
            reformulated_queries=[query] + reformulated,
            expansion_strategy="basic"
        )
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from query"""
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'are', 'do', 'does', 
            'what', 'how', 'can', 'you', 'have', 'me', 'tell', 'show', 'want', 'need'
        }
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        return [word for word in words if word not in stop_words]
    
    def _extract_menu_terms(self, content: str) -> List[str]:
        """Extract menu-specific terms from content"""
        food_pattern = r'\b(?:pizza|pasta|salad|sandwich|burger|soup|chicken|beef|fish|vegetarian|vegan|gluten.free|spicy|sweet|fresh)\b'
        return re.findall(food_pattern, content.lower())
    
    def _generate_reformulations(self, query: str, terms: List[str]) -> List[str]:
        """Generate reformulations using terms"""
        templates = [
            "What {term} options are available?",
            "Show me {term} items",
            "Do you have {term}?",
            "Tell me about your {term}"
        ]
        
        reformulated = []
        for template in templates[:2]:  # Limit templates
            for term in terms[:2]:  # Limit terms per template
                try:
                    reformulated.append(template.format(term=term))
                except:
                    continue
        
        return reformulated[:self.config.query_expansion_max_reformulations]
    
    def _llm_reformulate(self, query: str) -> List[str]:
        """Use LLM to generate reformulated queries"""
        if not self.llm:
            return []
        
        try:
            prompt = f"""
            Reformulate this hotel menu query in 2-3 different ways to find better information:
            "{query}"
            
            Return only the reformulated queries, one per line, without numbering.
            Focus on being more specific or using different food/menu terminology.
            """
            
            response = self.llm.invoke(prompt)
            reformulations = [line.strip() for line in response.content.split('\n') if line.strip()]
            return reformulations[:3]
            
        except Exception as e:
            logger.error(f"Error in LLM reformulation: {e}")
            return []
    
    def _template_reformulate(self, query: str, terms: List[str]) -> List[str]:
        """Generate template-based reformulations"""
        reformulations = []
        
        # Intent-specific templates
        if any(word in query.lower() for word in ['vegetarian', 'vegan', 'dietary']):
            reformulations.extend([
                "What dietary options do you offer?",
                "Show me plant-based menu items"
            ])
        elif any(word in query.lower() for word in ['price', 'cost', 'expensive']):
            reformulations.extend([
                "What are the menu prices?",
                "How much do items cost?"
            ])
        elif any(word in query.lower() for word in ['ingredient', 'contain', 'allergy']):
            reformulations.extend([
                "What ingredients are used?",
                "Do you have allergen information?"
            ])
        
        return reformulations[:self.config.query_expansion_max_reformulations]


# Global expander instance
_query_expander = None

def get_query_expander() -> SimplifiedQueryExpander:
    """Get the global query expander"""
    global _query_expander
    if _query_expander is None:
        _query_expander = SimplifiedQueryExpander()
    return _query_expander


def expand_user_query(query: str, metadata: Optional[Dict[str, Any]] = None) -> ExpansionResult:
    """Convenience function for query expansion"""
    expander = get_query_expander()
    return expander.expand_query(query, metadata)


if __name__ == "__main__":
    # Test the simplified query expander
    expander = get_query_expander()
    
    test_queries = [
        "what vegetarian options do you have",
        "pizza prices",
        "does salad contain nuts"
    ]
    
    print("Testing Simplified Query Expansion:")
    print("=" * 50)
    
    for query in test_queries:
        result = expander.expand_query(query, {"confidence": 0.8})
        print(f"Original: {result.original_query}")
        print(f"Strategy: {result.expansion_strategy}")
        print(f"Terms: {result.expanded_terms}")
        print(f"Reformulated: {result.reformulated_queries}")
        print("-" * 30)