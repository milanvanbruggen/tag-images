import numpy as np
from bs4 import BeautifulSoup
import re
import json
import cv2
import io
from cairosvg import svg2png
from PIL import Image

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
                    # Use keywords from categories.json
                    self.category_keywords[name] = [kw.lower() for kw in cat.get('keywords', [])]
                    # Set default complexity thresholds
                    self.complexity_thresholds[name] = self._get_default_threshold(name)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to empty categories if file cannot be read
            self.category_keywords = {}
            self.complexity_thresholds = {}

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

    def _svg_to_image(self, svg_content):
        """Convert SVG content to a numpy array image"""
        # Convert SVG to PNG with higher resolution for better analysis
        png_data = svg2png(bytestring=svg_content, output_width=800, output_height=800)
        
        # Convert PNG to numpy array
        img = Image.open(io.BytesIO(png_data))
        img_array = np.array(img)
        
        # Convert to grayscale while preserving image quality
        if len(img_array.shape) > 2:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
        
        # Apply slight blur to reduce noise
        img_array = cv2.GaussianBlur(img_array, (5, 5), 0)
        
        return img_array

    def _detect_shapes(self, image):
        """Detect shapes in the image using contour analysis"""
        # Create binary image with Otsu's thresholding
        _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours with hierarchy to detect nested shapes
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        shapes = {
            'circles': 0,
            'rectangles': 0,
            'triangles': 0,
            'other': 0
        }
        
        # Filter out very small contours (noise)
        min_area = image.shape[0] * image.shape[1] * 0.001
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        
        for i, contour in enumerate(contours):
            # Get perimeter and area
            perimeter = cv2.arcLength(contour, True)
            area = cv2.contourArea(contour)
            
            if perimeter == 0:
                continue
            
            # Calculate circularity (perfect circle = 1.0)
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            
            # Get convex hull for additional shape analysis
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = float(area) / hull_area if hull_area > 0 else 0
            
            # Fit ellipse for additional circle detection
            if len(contour) >= 5:
                ellipse = cv2.fitEllipse(contour)
                major_axis = max(ellipse[1])
                minor_axis = min(ellipse[1])
                axis_ratio = minor_axis / major_axis if major_axis > 0 else 0
            else:
                axis_ratio = 0
            
            # Enhanced circle detection
            is_circle = (circularity > 0.75 and solidity > 0.85) or (axis_ratio > 0.85 and solidity > 0.9)
            
            if is_circle:
                shapes['circles'] += 1
                continue
            
            # For non-circular shapes, analyze vertices
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            vertices = len(approx)
            
            # Get rotated rectangle for better shape analysis
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            width = rect[1][0]
            height = rect[1][1]
            aspect_ratio = min(width, height) / max(width, height) if max(width, height) > 0 else 0
            
            # Classify shapes based on vertices and properties
            if vertices == 3 or (vertices == 4 and aspect_ratio < 0.6):  # Triangle or triangular shape
                shapes['triangles'] += 1
            elif (vertices == 4 and aspect_ratio > 0.7) or (vertices <= 6 and aspect_ratio > 0.8):  # Rectangle/Square
                shapes['rectangles'] += 1
            else:
                shapes['other'] += 1
        
        return shapes, contours

    def analyze_svg(self, svg_content):
        """Analyseer SVG inhoud en retourneer waarschijnlijkheid per categorie"""
        try:
            image = self._svg_to_image(svg_content)
            shapes, contours = self._detect_shapes(image)
            
            scores = {}
            total_shapes = sum(shapes.values())
            
            if total_shapes == 0:
                return {name.lower(): 0.0 for name in self.category_keywords.keys()}
            
            for category_name in self.category_keywords.keys():
                category_name = category_name.lower()
                score = 0
                
                if 'round' in category_name or 'circle' in category_name:
                    if shapes['circles'] > 0:
                        # Perfect score for pure circles, high score for mostly circles
                        circle_ratio = shapes['circles'] / total_shapes
                        if circle_ratio == 1.0:
                            score = 1.0
                        elif circle_ratio > 0.5:
                            score = 0.9
                        else:
                            score = 0.7 * circle_ratio
                
                elif 'square' in category_name:
                    if shapes['rectangles'] > 0:
                        rect_ratio = shapes['rectangles'] / total_shapes
                        if rect_ratio == 1.0:
                            score = 1.0
                        elif rect_ratio > 0.5:
                            score = 0.9
                        else:
                            score = 0.7 * rect_ratio
                
                elif 'triangle' in category_name:
                    if shapes['triangles'] > 0:
                        tri_ratio = shapes['triangles'] / total_shapes
                        if tri_ratio == 1.0:
                            score = 1.0
                        elif tri_ratio > 0.5:
                            score = 0.9
                        else:
                            score = 0.7 * tri_ratio
                
                elif 'complex' in category_name or 'shape' in category_name:
                    # Score based on shape variety and complexity
                    unique_shapes = sum(1 for count in shapes.values() if count > 0)
                    if unique_shapes > 1:
                        variety_score = min(1.0, unique_shapes / 3)
                        count_score = min(1.0, total_shapes / 3)
                        score = (variety_score + count_score) / 2
                
                elif 'text' in category_name:
                    # Text detection would require OCR
                    score = 0.1
                
                elif 'heart' in category_name:
                    # Hearts typically have specific properties
                    if shapes['other'] > 0 and total_shapes <= 2:
                        score = 0.6
                
                elif 'arrow' in category_name:
                    # Arrows typically have a specific shape pattern
                    if shapes['other'] > 0 and total_shapes <= 3:
                        score = 0.6
                
                scores[category_name] = score
            
            return scores
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return {}

    def suggest_category(self, svg_content):
        """Suggereer de beste categorie voor een SVG"""
        scores = self.analyze_svg(svg_content)
        if not scores:
            return None, 0
        best_category, confidence = max(scores.items(), key=lambda x: x[1])
        return best_category, confidence 