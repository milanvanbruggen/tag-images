from bs4 import BeautifulSoup
import numpy as np
from svgpathtools import parse_path
import re
import json

class SVGAnalyzer:
    def __init__(self):
        self.update_categories_from_json()

    def update_categories_from_json(self, categories_file='categories.json'):
        """Update analyzer categories from JSON file"""
        try:
            with open(categories_file, 'r') as f:
                categories = json.load(f)
                
                # Initialize keywords for each category
                self.category_keywords = {}
                self.complexity_thresholds = {}
                
                for cat in categories:
                    name = cat['name'].lower()
                    # Use custom keywords if available, otherwise generate defaults
                    custom_keywords = [kw.lower() for kw in cat.get('keywords', [])]
                    if custom_keywords:
                        self.category_keywords[name] = custom_keywords
                    else:
                        self.category_keywords[name] = [name] + self._generate_keywords(name)
                    # Set default complexity thresholds
                    self.complexity_thresholds[name] = self._get_default_threshold(name)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to empty categories if file cannot be read
            self.category_keywords = {}
            self.complexity_thresholds = {}

    def _generate_keywords(self, category_name):
        """Generate relevant keywords for a category"""
        # Basic keyword generation rules
        keywords = []
        
        # Common variations and related terms
        if 'round' in category_name or 'circle' in category_name:
            keywords.extend(['circle', 'round', 'oval', 'ellipse', 'sphere'])
        elif 'square' in category_name or 'rectangle' in category_name:
            keywords.extend(['square', 'rectangle', 'block', 'box', 'quad'])
        elif 'triangle' in category_name:
            keywords.extend(['triangle', 'pyramid', 'wedge', 'delta'])
        elif 'text' in category_name:
            keywords.extend(['text', 'font', 'letter', 'word', 'character'])
        elif 'heart' in category_name:
            keywords.extend(['heart', 'love', 'valentine', 'cardiac'])
        elif 'arrow' in category_name:
            keywords.extend(['arrow', 'pointer', 'direction', 'navigate'])
        elif 'multi' in category_name or 'shape' in category_name:
            keywords.extend(['multiple', 'complex', 'combined', 'composite', 'mixed'])
            
        return keywords

    def _get_default_threshold(self, category_name):
        """Get default complexity threshold for a category"""
        if any(term in category_name for term in ['circle', 'round', 'square', 'triangle']):
            return (0, 30)  # Simple shapes
        elif 'text' in category_name:
            return (10, 50)  # Text elements
        elif 'arrow' in category_name:
            return (5, 40)  # Arrows
        elif 'heart' in category_name:
            return (20, 60)  # Hearts
        elif 'multi' in category_name or 'shape' in category_name:
            return (40, float('inf'))  # Complex shapes
        else:
            return (0, 100)  # Default range

    def analyze_svg(self, svg_content):
        """Analyseer SVG inhoud en retourneer waarschijnlijkheid per categorie"""
        # Update categories before analysis
        self.update_categories_from_json()
        
        if not self.category_keywords:
            return {}  # Return empty scores if no categories are defined
            
        soup = BeautifulSoup(svg_content, 'xml')
        
        # Bereken verschillende metrics
        complexity_score = self._calculate_complexity(soup)
        keyword_scores = self._analyze_keywords(svg_content)
        structure_score = self._analyze_structure(soup)
        
        # Combineer scores
        final_scores = {}
        for category_name in self.category_keywords.keys():
            # Gewogen gemiddelde van verschillende scores
            complexity_weight = self._complexity_weight(complexity_score, category_name)
            final_scores[category_name] = (
                0.4 * keyword_scores.get(category_name, 0) +
                0.4 * complexity_weight +
                0.2 * structure_score.get(category_name, 0)
            )
        
        return final_scores

    def _calculate_complexity(self, soup):
        """Bereken complexiteit score gebaseerd op SVG elementen"""
        # Tel aantal paden en vormen
        paths = len(soup.find_all('path'))
        shapes = len(soup.find_all(['rect', 'circle', 'ellipse', 'polygon', 'polyline']))
        
        # Tel aantal punten in paden
        total_points = 0
        for path in soup.find_all('path'):
            if path.get('d'):
                try:
                    path_obj = parse_path(path['d'])
                    total_points += len(path_obj)
                except:
                    pass
        
        # Combineer metrics tot een complexiteit score
        return paths * 5 + shapes * 3 + total_points * 0.1

    def _analyze_keywords(self, svg_content):
        """Analyseer SVG inhoud voor category-specifieke keywords"""
        scores = {}
        content_lower = svg_content.lower()
        
        for category_name, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                matches = len(re.findall(r'\b' + keyword + r'\b', content_lower))
                score += matches
            scores[category_name] = min(1.0, score * 0.2)  # Normaliseer score
            
        return scores

    def _analyze_structure(self, soup):
        """Analyseer SVG structuur voor category-specifieke patronen"""
        scores = {}
        
        # Tel verschillende soorten elementen
        elements = {
            'path': len(soup.find_all('path')),
            'group': len(soup.find_all('g')),
            'circle': len(soup.find_all('circle')),
            'ellipse': len(soup.find_all('ellipse')),
            'rect': len(soup.find_all('rect')),
            'polygon': len(soup.find_all('polygon')),
            'text': len(soup.find_all('text')),
            'total': len(soup.find_all())
        }
        
        # Bereken scores voor elke categorie
        for category_name in self.category_keywords.keys():
            scores[category_name] = self._calculate_structure_score(category_name, elements)
        
        return scores

    def _calculate_structure_score(self, category_name, elements):
        """Calculate structure score based on category type"""
        if elements['total'] == 0:
            return 0
            
        score = 0
        if 'round' in category_name or 'circle' in category_name:
            # Check for circles and ellipses
            round_shapes = elements['circle'] + elements['ellipse']
            score = round_shapes / max(1, elements['total'])
        elif 'square' in category_name:
            # Check for rectangles and polygons
            square_shapes = elements['rect'] + elements['polygon']
            score = square_shapes / max(1, elements['total'])
        elif 'text' in category_name:
            text_present = 1 if elements['text'] > 0 else 0
            score = text_present
        elif 'multi' in category_name or 'shape' in category_name:
            # Higher score for more complex structures
            complexity_ratio = min(1.0, elements['total'] / 10)
            shape_types = sum(1 for k, v in elements.items() if k != 'total' and v > 0)
            score = (complexity_ratio + shape_types / (len(elements) - 1)) / 2
        else:
            # Default scoring based on general shape presence
            total_shapes = sum(elements[k] for k in ['circle', 'ellipse', 'rect', 'polygon'])
            shape_ratio = total_shapes / max(1, elements['total'])
            path_ratio = elements['path'] / max(1, elements['total'])
            score = (shape_ratio + path_ratio) / 2
            
        return min(1.0, score)  # Normalize score to max 1.0

    def _complexity_weight(self, complexity_score, category_name):
        """Bereken gewicht gebaseerd op complexiteit voor een categorie"""
        min_score, max_score = self.complexity_thresholds.get(category_name, (0, 100))
        
        if complexity_score < min_score:
            return max(0, 1 - (min_score - complexity_score) / min_score)
        elif complexity_score > max_score:
            return max(0, 1 - (complexity_score - max_score) / max_score)
        else:
            return 1.0

    def suggest_category(self, svg_content):
        """Suggereer de beste categorie voor een SVG"""
        scores = self.analyze_svg(svg_content)
        if not scores:
            return None, 0
        best_category, confidence = max(scores.items(), key=lambda x: x[1])
        return best_category, confidence 