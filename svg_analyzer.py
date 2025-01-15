from bs4 import BeautifulSoup
import numpy as np
from svgpathtools import parse_path
import re

class SVGAnalyzer:
    def __init__(self):
        # Voorgedefinieerde keywords per categorie
        self.category_keywords = {
            'icons': ['icon', 'glyph', 'symbol', 'button', 'menu', 'ui', 'interface'],
            'logos': ['logo', 'brand', 'company', 'trademark', 'identity'],
            'illustrations': ['illustration', 'scene', 'character', 'background', 'drawing']
        }
        
        # Complexiteit drempels
        self.complexity_thresholds = {
            'icons': (0, 50),        # Icons zijn meestal simpel
            'logos': (20, 100),      # Logo's hebben gemiddelde complexiteit
            'illustrations': (70, float('inf'))  # Illustraties zijn meestal complex
        }

    def analyze_svg(self, svg_content):
        """Analyseer SVG inhoud en retourneer waarschijnlijkheid per categorie"""
        soup = BeautifulSoup(svg_content, 'xml')
        
        # Bereken verschillende metrics
        complexity_score = self._calculate_complexity(soup)
        keyword_scores = self._analyze_keywords(svg_content)
        structure_score = self._analyze_structure(soup)
        
        # Combineer scores
        final_scores = {}
        for category in self.category_keywords.keys():
            # Gewogen gemiddelde van verschillende scores
            complexity_weight = self._complexity_weight(complexity_score, category)
            final_scores[category] = (
                0.4 * keyword_scores.get(category, 0) +
                0.4 * complexity_weight +
                0.2 * structure_score.get(category, 0)
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
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                matches = len(re.findall(r'\b' + keyword + r'\b', content_lower))
                score += matches
            scores[category] = min(1.0, score * 0.2)  # Normaliseer score
            
        return scores

    def _analyze_structure(self, soup):
        """Analyseer SVG structuur voor category-specifieke patronen"""
        scores = {}
        
        # Tel verschillende soorten elementen
        elements = {
            'path': len(soup.find_all('path')),
            'group': len(soup.find_all('g')),
            'shapes': len(soup.find_all(['rect', 'circle', 'ellipse', 'polygon'])),
            'text': len(soup.find_all('text')),
            'total': len(soup.find_all())
        }
        
        # Bereken scores per categorie gebaseerd op structuur
        scores['icons'] = self._calculate_icon_structure_score(elements)
        scores['logos'] = self._calculate_logo_structure_score(elements)
        scores['illustrations'] = self._calculate_illustration_structure_score(elements)
        
        return scores

    def _complexity_weight(self, complexity_score, category):
        """Bereken gewicht gebaseerd op complexiteit voor een categorie"""
        min_score, max_score = self.complexity_thresholds[category]
        
        if complexity_score < min_score:
            return max(0, 1 - (min_score - complexity_score) / min_score)
        elif complexity_score > max_score:
            return max(0, 1 - (complexity_score - max_score) / max_score)
        else:
            return 1.0

    def _calculate_icon_structure_score(self, elements):
        """Bereken structuur score voor icons"""
        if elements['total'] == 0:
            return 0
        
        # Icons zijn meestal simpel met weinig groepen
        simple_ratio = 1 - (elements['group'] / elements['total'])
        shape_ratio = elements['shapes'] / elements['total']
        
        return (simple_ratio + shape_ratio) / 2

    def _calculate_logo_structure_score(self, elements):
        """Bereken structuur score voor logos"""
        if elements['total'] == 0:
            return 0
        
        # Logo's hebben vaak text en zijn gegroepeerd
        text_present = 1 if elements['text'] > 0 else 0
        group_ratio = elements['group'] / elements['total']
        
        return (text_present + group_ratio) / 2

    def _calculate_illustration_structure_score(self, elements):
        """Bereken structuur score voor illustraties"""
        if elements['total'] == 0:
            return 0
        
        # Illustraties zijn complex met veel paden en groepen
        path_ratio = elements['path'] / elements['total']
        complexity_ratio = elements['total'] / 10  # Genormaliseerd voor grote illustraties
        
        return min(1.0, (path_ratio + min(1.0, complexity_ratio)) / 2)

    def suggest_category(self, svg_content):
        """Suggereer de beste categorie voor een SVG"""
        scores = self.analyze_svg(svg_content)
        return max(scores.items(), key=lambda x: x[1]) 