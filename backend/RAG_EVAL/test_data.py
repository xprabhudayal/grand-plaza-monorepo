"""
Test Data Generator for RAG Evaluation
Generates comprehensive test cases covering all edge cases and scenarios
"""

import pandas as pd
import numpy as np
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import itertools
from faker import Faker
from loguru import logger

from .metrics import RAGTestCase

fake = Faker()

@dataclass
class MenuItem:
    """Menu item data structure"""
    name: str
    category: str
    description: str
    price: float
    ingredients: List[str]
    dietary_info: List[str]  # vegetarian, vegan, gluten-free, etc.
    calories: Optional[int] = None
    availability: bool = True
    allergens: Optional[List[str]] = None

class TestDataGenerator:
    """Generates comprehensive test data for RAG evaluation"""
    
    def __init__(self, menu_data_path: Optional[str] = None):
        self.menu_items = []
        self.query_templates = self._load_query_templates()
        self.edge_case_scenarios = self._define_edge_cases()
        
        if menu_data_path:
            self.load_menu_data(menu_data_path)
        else:
            self.generate_synthetic_menu()
    
    def load_menu_data(self, file_path: str):
        """Load menu data from CSV or JSON file"""
        try:
            path = Path(file_path)
            if path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
                self.menu_items = self._dataframe_to_menu_items(df)
            elif path.suffix.lower() == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.menu_items = [MenuItem(**item) for item in data]
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
            
            logger.info(f"Loaded {len(self.menu_items)} menu items from {file_path}")
            
        except Exception as e:
            logger.warning(f"Could not load menu data from {file_path}: {e}")
            logger.info("Generating synthetic menu data instead")
            self.generate_synthetic_menu()
    
    def _dataframe_to_menu_items(self, df: pd.DataFrame) -> List[MenuItem]:
        """Convert DataFrame to MenuItem objects"""
        items = []
        
        for _, row in df.iterrows():
            item = MenuItem(
                name=row.get('Item Name', ''),
                category=row.get('Section', 'General'),
                description=row.get('Description', ''),
                price=float(row.get('Price (USD)', 0)),
                ingredients=str(row.get('Description', '')).split(',') if pd.notna(row.get('Description')) else [],
                dietary_info=[row.get('Veg/Non-Veg', '')] if pd.notna(row.get('Veg/Non-Veg')) else [],
                calories=int(row.get('Calories (kcal)', 0)) if pd.notna(row.get('Calories (kcal)')) else None
            )
            items.append(item)
        
        return items
    
    def generate_synthetic_menu(self):
        """Generate synthetic menu data for testing"""
        categories = {
            'Breakfast': [
                ('American Breakfast', 'Eggs, bacon, toast, hash browns', 12.99, ['eggs', 'bacon', 'bread', 'potatoes']),
                ('Continental Breakfast', 'Pastries, fruits, cereals', 8.99, ['pastries', 'fruits', 'cereals']),
                ('Pancakes', 'Stack of 3 with syrup and butter', 9.99, ['flour', 'eggs', 'milk', 'butter', 'syrup']),
                ('Omelet', 'Choice of fillings', 11.99, ['eggs', 'cheese', 'vegetables']),
            ],
            'Appetizers': [
                ('Caesar Salad', 'Crisp romaine, parmesan, croutons', 8.99, ['romaine', 'parmesan', 'croutons']),
                ('Soup of the Day', 'Ask for today\'s selection', 6.99, ['vegetables', 'broth']),
                ('Chicken Wings', 'Buffalo or BBQ style', 10.99, ['chicken', 'sauce']),
                ('Garlic Bread', 'Fresh baked with herbs', 5.99, ['bread', 'garlic', 'herbs']),
            ],
            'Main Courses': [
                ('Grilled Chicken', 'With vegetables and rice', 18.99, ['chicken', 'vegetables', 'rice']),
                ('Beef Steak', '8oz sirloin with potato', 24.99, ['beef', 'potato']),
                ('Pasta Marinara', 'Fresh tomato sauce', 14.99, ['pasta', 'tomatoes', 'herbs']),
                ('Fish and Chips', 'Beer battered cod', 16.99, ['cod', 'potatoes', 'batter']),
            ],
            'Sandwiches': [
                ('Club Sandwich', 'Turkey, bacon, lettuce, tomato', 12.99, ['turkey', 'bacon', 'lettuce', 'tomato', 'bread']),
                ('Cheeseburger', 'Beef patty with cheese and fries', 14.99, ['beef', 'cheese', 'bun', 'fries']),
                ('Chicken Wrap', 'Grilled chicken with vegetables', 11.99, ['chicken', 'vegetables', 'tortilla']),
                ('Veggie Sandwich', 'Fresh vegetables and hummus', 9.99, ['vegetables', 'hummus', 'bread']),
            ],
            'Desserts': [
                ('Chocolate Cake', 'Rich chocolate layer cake', 7.99, ['chocolate', 'flour', 'sugar', 'butter']),
                ('Ice Cream', 'Vanilla, chocolate, or strawberry', 5.99, ['milk', 'cream', 'sugar']),
                ('Apple Pie', 'Classic with vanilla ice cream', 6.99, ['apples', 'flour', 'sugar', 'cinnamon']),
                ('Fruit Salad', 'Fresh seasonal fruits', 5.99, ['fruits']),
            ],
            'Beverages': [
                ('Coffee', 'Fresh brewed', 3.99, ['coffee beans']),
                ('Tea', 'Various herbal and black teas', 3.99, ['tea leaves']),
                ('Fresh Juice', 'Orange, apple, cranberry', 4.99, ['fruits']),
                ('Soft Drinks', 'Coke, Pepsi, Sprite', 2.99, ['carbonated water', 'syrup']),
            ]
        }
        
        dietary_options = ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'non-vegetarian']
        allergens = ['nuts', 'dairy', 'gluten', 'shellfish', 'eggs']
        
        for category, items in categories.items():
            for name, description, price, ingredients in items:
                # Add some variation
                actual_price = price + random.uniform(-1, 1)
                dietary = [random.choice(dietary_options)]
                item_allergens = random.sample(allergens, random.randint(0, 2))
                
                menu_item = MenuItem(
                    name=name,
                    category=category,
                    description=description,
                    price=round(actual_price, 2),
                    ingredients=ingredients,
                    dietary_info=dietary,
                    calories=random.randint(200, 800) if category != 'Beverages' else random.randint(0, 200),
                    availability=random.choice([True, True, True, False]),  # 75% available
                    allergens=item_allergens
                )
                
                self.menu_items.append(menu_item)
        
        logger.info(f"Generated {len(self.menu_items)} synthetic menu items")
    
    def _load_query_templates(self) -> Dict[str, List[str]]:
        """Define query templates for different scenarios"""
        return {
            'basic_info': [
                "What is {item_name}?",
                "Tell me about {item_name}",
                "Can you describe {item_name}?",
                "What's in {item_name}?",
                "How much does {item_name} cost?",
                "What's the price of {item_name}?",
            ],
            'category_queries': [
                "What {category} items do you have?",
                "Show me the {category} menu",
                "What's available in {category}?",
                "List all {category} items",
                "What {category} dishes do you serve?",
            ],
            'dietary_queries': [
                "What vegetarian options do you have?",
                "Do you have vegan {category}?",
                "What gluten-free items are available?",
                "Show me dairy-free options",
                "What {category} items are vegetarian?",
            ],
            'price_queries': [
                "What's the cheapest {category} item?",
                "What costs less than ${price}?",
                "Show me items under ${price}",
                "What's the most expensive item?",
                "Items between ${price1} and ${price2}?",
            ],
            'availability_queries': [
                "Is {item_name} available?",
                "Do you have {item_name} today?",
                "What's available right now?",
                "What's not available?",
            ],
            'ingredient_queries': [
                "What has {ingredient}?",
                "Items without {ingredient}",
                "Does {item_name} contain {ingredient}?",
                "What ingredients are in {item_name}?",
            ],
            'comparison_queries': [
                "Compare {item1} and {item2}",
                "What's the difference between {item1} and {item2}?",
                "Which is better: {item1} or {item2}?",
            ],
            'complex_queries': [
                "What vegetarian {category} items cost less than ${price}?",
                "Show me gluten-free options with less than {calories} calories",
                "What {category} items don't contain {allergen}?",
                "Recommend something vegetarian and under ${price}",
            ]
        }
    
    def _define_edge_cases(self) -> Dict[str, List[str]]:
        """Define edge case scenarios"""
        return {
            'empty_queries': ['', ' ', '   '],
            'nonsensical_queries': [
                'purple elephant sandwich',
                'quantum burger with time sauce',
                'invisible menu item',
                'negative price food'
            ],
            'ambiguous_queries': [
                'food',
                'something good',
                'what do you have',
                'menu',
                'stuff'
            ],
            'typos_and_misspellings': [
                'checken',  # chicken
                'vegitarian',  # vegetarian
                'tomatoe',  # tomato
                'burguer',  # burger
                'avalable'  # available
            ],
            'multiple_items': [
                'chicken and beef',
                'all desserts and beverages',
                'everything with cheese',
                'pasta, pizza, and salad'
            ],
            'contradictory_queries': [
                'vegan meat burger',
                'dairy-free cheese pizza',
                'sugar-free chocolate cake',
                'gluten-free bread'
            ],
            'out_of_context': [
                'weather forecast',
                'book a flight',
                'play music',
                'what time is it'
            ],
            'extremely_long': [
                'I am looking for a very specific type of food item that has particular ingredients and meets certain dietary requirements and falls within a specific price range and is available today and doesnt contain allergens and has low calories and tastes really good and is popular among customers'
            ],
            'special_characters': [
                'item with $pecial ch@racters!',
                'food & drinks',
                'menu (vegetarian)',
                'price: $10-15'
            ]
        }
    
    def generate_basic_test_cases(self, count: int = 50) -> List[RAGTestCase]:
        """Generate basic test cases from menu items"""
        test_cases = []
        
        for _ in range(count):
            # Select random menu item
            item = random.choice(self.menu_items)
            
            # Select random query template
            template_category = random.choice(list(self.query_templates.keys()))
            template = random.choice(self.query_templates[template_category])
            
            # Fill template with item data
            query = self._fill_template(template, item)
            
            # Generate expected context
            expected_contexts = [self._item_to_context(item)]
            
            # Generate ground truth answer
            ground_truth = self._generate_ground_truth(query, item)
            
            test_case = RAGTestCase(
                query=query,
                retrieved_contexts=[],  # Will be filled by RAG system
                generated_answer='',    # Will be filled by RAG system
                ground_truth=ground_truth,
                expected_contexts=expected_contexts,
                metadata={
                    'item_name': item.name,
                    'category': item.category,
                    'expected_price': str(item.price),
                    'expected_ingredients': item.ingredients,
                    'expected_category': item.category,
                    'test_type': 'basic',
                    'template_category': template_category
                }
            )
            
            test_cases.append(test_case)
        
        return test_cases
    
    def generate_edge_case_tests(self) -> List[RAGTestCase]:
        """Generate edge case test scenarios"""
        test_cases = []
        
        for scenario_name, queries in self.edge_case_scenarios.items():
            for query in queries:
                test_case = RAGTestCase(
                    query=query,
                    retrieved_contexts=[],
                    generated_answer='',
                    ground_truth=self._generate_edge_case_ground_truth(query, scenario_name),
                    expected_contexts=[],
                    metadata={
                        'test_type': 'edge_case',
                        'scenario': scenario_name,
                        'expected_behavior': self._get_expected_behavior(scenario_name)
                    }
                )
                test_cases.append(test_case)
        
        return test_cases
    
    def generate_stress_test_cases(self, count: int = 20) -> List[RAGTestCase]:
        """Generate stress test cases with high complexity"""
        test_cases = []
        
        for _ in range(count):
            # Generate complex multi-constraint queries
            constraints = random.sample([
                'vegetarian',
                'under $15',
                'gluten-free',
                'low calorie',
                'contains cheese',
                'no nuts'
            ], random.randint(2, 4))
            
            query = f"Find me something that is {' and '.join(constraints)}"
            
            # Find items that match constraints
            matching_items = self._find_matching_items(constraints)
            expected_contexts = [self._item_to_context(item) for item in matching_items[:3]]
            
            test_case = RAGTestCase(
                query=query,
                retrieved_contexts=[],
                generated_answer='',
                ground_truth=self._generate_complex_ground_truth(query, matching_items),
                expected_contexts=expected_contexts,
                metadata={
                    'test_type': 'stress_test',
                    'constraints': constraints,
                    'matching_items_count': len(matching_items)
                }
            )
            
            test_cases.append(test_case)
        
        return test_cases
    
    def generate_conversation_context_tests(self, count: int = 15) -> List[RAGTestCase]:
        """Generate test cases that require conversation context"""
        test_cases = []
        
        conversation_scenarios = [
            {
                'previous_query': 'What desserts do you have?',
                'follow_up': 'Which one has chocolate?',
                'context_needed': True
            },
            {
                'previous_query': 'Show me breakfast items',
                'follow_up': 'What about the vegetarian ones?',
                'context_needed': True
            },
            {
                'previous_query': 'I want something under $10',
                'follow_up': 'Make it vegetarian',
                'context_needed': True
            }
        ]
        
        for scenario in conversation_scenarios:
            test_case = RAGTestCase(
                query=scenario['follow_up'],
                retrieved_contexts=[],
                generated_answer='',
                ground_truth='',  # Context-dependent
                expected_contexts=[],
                metadata={
                    'test_type': 'conversation_context',
                    'previous_query': scenario['previous_query'],
                    'requires_context': scenario['context_needed']
                }
            )
            test_cases.append(test_case)
        
        return test_cases
    
    def _fill_template(self, template: str, item: MenuItem) -> str:
        """Fill query template with menu item data"""
        return template.format(
            item_name=item.name,
            category=item.category.lower(),
            price=item.price,
            price1=item.price - 5,
            price2=item.price + 5,
            ingredient=random.choice(item.ingredients) if item.ingredients else 'cheese',
            allergen=random.choice(item.allergens) if item.allergens else 'nuts',
            calories=item.calories or 500,
            item1=item.name,
            item2=random.choice(self.menu_items).name
        )
    
    def _item_to_context(self, item: MenuItem) -> str:
        """Convert menu item to context string"""
        context = f"Category: {item.category}\n"
        context += f"Item: {item.name}\n"
        context += f"Description: {item.description}\n"
        context += f"Price: ${item.price}\n"
        
        if item.ingredients:
            context += f"Ingredients: {', '.join(item.ingredients)}\n"
        
        if item.dietary_info:
            context += f"Dietary: {', '.join(item.dietary_info)}\n"
        
        if item.calories:
            context += f"Calories: {item.calories}\n"
        
        context += f"Available: {'Yes' if item.availability else 'No'}\n"
        
        return context.strip()
    
    def _generate_ground_truth(self, query: str, item: MenuItem) -> str:
        """Generate ground truth answer for a query about an item"""
        query_lower = query.lower()
        
        if 'what is' in query_lower or 'describe' in query_lower:
            return f"{item.name} is a {item.category.lower()} item. {item.description}. It costs ${item.price}."
        
        elif 'cost' in query_lower or 'price' in query_lower:
            return f"{item.name} costs ${item.price}."
        
        elif 'ingredient' in query_lower or 'what\'s in' in query_lower:
            ingredients = ', '.join(item.ingredients) if item.ingredients else 'ingredients not specified'
            return f"{item.name} contains: {ingredients}."
        
        elif 'available' in query_lower:
            availability = 'available' if item.availability else 'not available'
            return f"{item.name} is currently {availability}."
        
        else:
            return f"{item.name} is a {item.category.lower()} item that costs ${item.price}. {item.description}"
    
    def _generate_edge_case_ground_truth(self, query: str, scenario: str) -> str:
        """Generate expected responses for edge cases"""
        if scenario == 'empty_queries':
            return "I'd be happy to help you with our menu. What would you like to know about?"
        
        elif scenario == 'nonsensical_queries':
            return "I don't have information about that. Would you like to see our actual menu items?"
        
        elif scenario == 'ambiguous_queries':
            return "Could you be more specific? I can help you with our breakfast, appetizers, main courses, sandwiches, desserts, or beverages."
        
        elif scenario == 'out_of_context':
            return "I'm here to help with our hotel menu. Is there something from our food or beverage selection you'd like to know about?"
        
        else:
            return "I'll do my best to help you with that request."
    
    def _get_expected_behavior(self, scenario: str) -> str:
        """Define expected system behavior for edge cases"""
        behaviors = {
            'empty_queries': 'Polite prompt for clarification',
            'nonsensical_queries': 'Graceful rejection with redirect to menu',
            'ambiguous_queries': 'Request for clarification with options',
            'typos_and_misspellings': 'Attempt fuzzy matching or suggest corrections',
            'contradictory_queries': 'Explain contradiction and offer alternatives',
            'out_of_context': 'Redirect to menu-related topics',
            'extremely_long': 'Extract key requirements and respond',
            'special_characters': 'Handle gracefully, ignore special chars'
        }
        return behaviors.get(scenario, 'Handle appropriately')
    
    def _find_matching_items(self, constraints: List[str]) -> List[MenuItem]:
        """Find menu items matching given constraints"""
        matching = []
        
        for item in self.menu_items:
            matches = True
            
            for constraint in constraints:
                if 'vegetarian' in constraint:
                    if 'vegetarian' not in item.dietary_info and 'vegan' not in item.dietary_info:
                        matches = False
                        break
                
                elif 'under $' in constraint:
                    price_limit = float(constraint.split('$')[1])
                    if item.price >= price_limit:
                        matches = False
                        break
                
                elif 'gluten-free' in constraint:
                    if 'gluten-free' not in item.dietary_info:
                        matches = False
                        break
                
                elif 'low calorie' in constraint:
                    if item.calories and item.calories > 400:
                        matches = False
                        break
                
                elif 'contains' in constraint:
                    ingredient = constraint.split('contains ')[1]
                    if ingredient not in ' '.join(item.ingredients).lower():
                        matches = False
                        break
                
                elif 'no ' in constraint:
                    avoid_ingredient = constraint.split('no ')[1]
                    if avoid_ingredient in ' '.join(item.ingredients).lower():
                        matches = False
                        break
            
            if matches:
                matching.append(item)
        
        return matching
    
    def _generate_complex_ground_truth(self, query: str, matching_items: List[MenuItem]) -> str:
        """Generate ground truth for complex queries"""
        if not matching_items:
            return "I don't have any items that match all those requirements. Would you like to adjust your criteria?"
        
        if len(matching_items) == 1:
            item = matching_items[0]
            return f"I found one item that matches: {item.name} from our {item.category} menu. It costs ${item.price}. {item.description}"
        
        else:
            items_list = [f"{item.name} (${item.price})" for item in matching_items[:3]]
            return f"I found {len(matching_items)} items that match your criteria. Here are some options: {', '.join(items_list)}."
    
    def generate_complete_test_suite(self) -> Dict[str, List[RAGTestCase]]:
        """Generate complete test suite with all categories"""
        return {
            'basic_tests': self.generate_basic_test_cases(50),
            'edge_cases': self.generate_edge_case_tests(),
            'stress_tests': self.generate_stress_test_cases(20),
            'conversation_context': self.generate_conversation_context_tests(15)
        }
    
    def save_test_data(self, test_suite: Dict[str, List[RAGTestCase]], output_dir: str):
        """Save generated test data to files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        for category, test_cases in test_suite.items():
            # Convert to serializable format
            serializable_cases = []
            for case in test_cases:
                case_dict = asdict(case)
                serializable_cases.append(case_dict)
            
            # Save to JSON
            file_path = output_path / f"{category}.json"
            with open(file_path, 'w') as f:
                json.dump(serializable_cases, f, indent=2)
            
            logger.info(f"Saved {len(test_cases)} test cases to {file_path}")
        
        # Save menu data for reference
        menu_file = output_path / "menu_data.json"
        menu_data = [asdict(item) for item in self.menu_items]
        with open(menu_file, 'w') as f:
            json.dump(menu_data, f, indent=2)
        
        logger.info(f"Saved menu data to {menu_file}")
    
    def load_test_data(self, input_dir: str) -> Dict[str, List[RAGTestCase]]:
        """Load test data from files"""
        input_path = Path(input_dir)
        test_suite = {}
        
        for json_file in input_path.glob("*.json"):
            if json_file.name == "menu_data.json":
                continue
            
            category = json_file.stem
            with open(json_file, 'r') as f:
                case_dicts = json.load(f)
            
            test_cases = [RAGTestCase(**case_dict) for case_dict in case_dicts]
            test_suite[category] = test_cases
            
            logger.info(f"Loaded {len(test_cases)} test cases from {json_file}")
        
        return test_suite