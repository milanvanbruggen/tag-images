import streamlit as st
import os
from pathlib import Path
import shutil
import json
from svg_analyzer import SVGAnalyzer
import pandas as pd
import uuid
import streamlit.components.v1 as components

# Set page config
st.set_page_config(
    page_title="SVG Categorizer",
    page_icon="🏷️",
    layout="wide"
)

# Constants for file paths
DEFAULT_IMAGES_DIR = "images"
CATEGORIES_FILE = "categories.json"
CATEGORIZATION_FILE = "categorized_images.json"

class Category:
    def __init__(self, id, name, keywords=None):
        self.id = id
        self.name = name
        self.keywords = keywords or []

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'keywords': self.keywords
        }

    @staticmethod
    def from_dict(data):
        return Category(data['id'], data['name'], data.get('keywords', []))

def load_categories():
    """Load categories from JSON file"""
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'r') as f:
            categories_data = json.load(f)
            return {cat['id']: Category.from_dict(cat) for cat in categories_data}
    
    # Default categories with generated IDs
    default_categories = {
        str(uuid.uuid4()): Category(str(uuid.uuid4()), 'icons', ['icon', 'symbol', 'glyph']),
        str(uuid.uuid4()): Category(str(uuid.uuid4()), 'logos', ['logo', 'brand', 'company']),
        str(uuid.uuid4()): Category(str(uuid.uuid4()), 'illustrations', ['illustration', 'scene', 'drawing'])
    }
    save_categories(default_categories)
    return default_categories

def save_categories(categories):
    """Save categories to JSON file"""
    categories_data = [cat.to_dict() for cat in categories.values()]
    with open(CATEGORIES_FILE, 'w') as f:
        json.dump(categories_data, f, indent=4)

def load_categorization():
    """Load categorization data from JSON file"""
    if os.path.exists(CATEGORIZATION_FILE):
        try:
            with open(CATEGORIZATION_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # Only try to parse if file is not empty
                    return json.loads(content)
        except json.JSONDecodeError:
            pass  # If there's an error reading the JSON, return empty dict
    return {}

def save_categorization(filename, category_id, scores=None):
    """Save the categorization to a JSON file"""
    data = load_categorization()
    
    data[filename] = {
        'category_id': category_id,
        'analysis_scores': scores,
        'timestamp': str(pd.Timestamp.now())
    }
    
    with open(CATEGORIZATION_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_uncategorized_files():
    """Get list of uncategorized SVG files from default directory"""
    if not os.path.exists(DEFAULT_IMAGES_DIR):
        os.makedirs(DEFAULT_IMAGES_DIR)
    
    categorized = load_categorization()
    all_files = [f for f in os.listdir(DEFAULT_IMAGES_DIR) if f.lower().endswith('.svg')]
    return [f for f in all_files if f not in categorized]

def read_svg_file(filepath):
    """Read SVG file content"""
    with open(filepath, 'rb') as f:
        return f.read()

def rename_category_directory(old_name, new_name):
    """Rename category directory if it exists"""
    if os.path.exists(old_name):
        os.rename(old_name, new_name)

# Initialize session state
if 'categories' not in st.session_state:
    st.session_state.categories = load_categories()
if 'current_file_index' not in st.session_state:
    st.session_state.current_file_index = 0
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = SVGAnalyzer()
if 'using_uploaded_files' not in st.session_state:
    st.session_state.using_uploaded_files = False
if 'editing_category' not in st.session_state:
    st.session_state.editing_category = None

def remove_categorization(filename):
    """Remove categorization for a file"""
    data = load_categorization()
    if filename in data:
        del data[filename]
        with open(CATEGORIZATION_FILE, 'w') as f:
            json.dump(data, f, indent=4)

def show_categorized_files():
    """Show overview of categorized files grouped by category"""
    categorization = load_categorization()
    if not categorization:
        st.info("Nog geen bestanden gecategoriseerd")
        return
    
    # Group files by category
    files_by_category = {}
    for filename, data in categorization.items():
        category_id = data['category_id']
        if category_id in st.session_state.categories:
            category_name = st.session_state.categories[category_id].name
            if category_name not in files_by_category:
                files_by_category[category_name] = []
            files_by_category[category_name].append((filename, data))
    
    # Display files by category
    for category_name, files in sorted(files_by_category.items()):
        with st.expander(f"{category_name} ({len(files)} bestanden)"):
            for filename, data in sorted(files, key=lambda x: x[0]):
                col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 1])
                filepath = os.path.join(DEFAULT_IMAGES_DIR, filename)
                if os.path.exists(filepath):
                    col1.write(filename)
                    col2.image(filepath, width=50)
                    timestamp = pd.Timestamp(data['timestamp']).strftime("%Y-%m-%d %H:%M")
                    col3.write(f"Gecategoriseerd op: {timestamp}")
                    
                    # Add category selection dropdown
                    current_cat_id = data['category_id']
                    categories_dict = {cat.name: cat_id for cat_id, cat in st.session_state.categories.items()}
                    new_category = col4.selectbox(
                        "Categorie",
                        options=sorted(categories_dict.keys()),
                        key=f"cat_select_{filename}",
                        index=sorted(categories_dict.keys()).index(category_name)
                    )
                    
                    # Add remove button
                    if col5.button("🗑️", key=f"remove_{filename}", help="Verwijder categorisering"):
                        remove_categorization(filename)
                        st.success(f"Categorisering verwijderd voor: {filename}")
                        st.rerun()
                    
                    # If category changed, update categorization
                    if categories_dict[new_category] != current_cat_id:
                        # Read current SVG content for analysis
                        with open(filepath, 'r') as f:
                            svg_content = f.read()
                        scores = st.session_state.analyzer.analyze_svg(svg_content)
                        save_categorization(filename, categories_dict[new_category], scores)
                        st.rerun()

def show_next_uncategorized_file(auto_categorize, confidence_threshold):
    """Show and process the next uncategorized file"""
    uncategorized = get_uncategorized_files()
    if not uncategorized:
        st.info(f"Geen ongecategoriseerde bestanden gevonden in {DEFAULT_IMAGES_DIR}")
        st.write(f"Plaats SVG bestanden in de '{DEFAULT_IMAGES_DIR}' map om ze te categoriseren")
        return

    # Initialize current index in session state if not exists
    if 'current_file_index' not in st.session_state:
        st.session_state.current_file_index = 0
    
    # Navigation and file info in one container with gray background
    nav_container = st.container()
    with nav_container:
        st.markdown("""
            <style>
            [data-testid="stVerticalBlock"] > div:has(button:contains("⬅️")) {
                background-color: #f0f2f6;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
            }
            [data-testid="stVerticalBlock"] > div:has(button:contains("⬅️")) > div {
                margin-bottom: 0;
            }
            [data-testid="stVerticalBlock"] > div:has(button:contains("⬅️")) [data-testid="stCaption"] {
                margin-top: 0.5rem;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Navigation row
        nav_col1, nav_col2 = st.columns([8, 2])
        
        # Left side: navigation buttons
        with nav_col1:
            nav_buttons_col1, nav_buttons_col2, nav_buttons_col3 = st.columns([1, 1, 18])
            with nav_buttons_col1:
                if st.button("⬅️", disabled=st.session_state.current_file_index == 0):
                    st.session_state.current_file_index = max(0, st.session_state.current_file_index - 1)
                    if 'current_analysis' in st.session_state:
                        del st.session_state.current_analysis
                    st.rerun()
            with nav_buttons_col2:
                if st.button("➡️", disabled=st.session_state.current_file_index == len(uncategorized) - 1):
                    st.session_state.current_file_index = min(len(uncategorized) - 1, st.session_state.current_file_index + 1)
                    if 'current_analysis' in st.session_state:
                        del st.session_state.current_analysis
                    st.rerun()
        
        # Right side: file counter
        with nav_col2:
            st.write(f"Afbeelding {st.session_state.current_file_index + 1} van {len(uncategorized)}")
        
        # Display current file name below navigation
        current_file = uncategorized[st.session_state.current_file_index]
        filepath = os.path.join(DEFAULT_IMAGES_DIR, current_file)
        st.caption(f"Categoriseren: {current_file}")
    
    # Add CSS for sticky buttons and image size
    st.markdown("""
        <style>
        .element-container img {
            max-height: 50vh !important;
            width: auto !important;
            display: block !important;
            margin: auto !important;
            margin-bottom: 0 !important;
        }
        [data-testid="caption"] {
            margin-top: 0.2rem !important;
        }
        .main-content {
            margin-bottom: 120px;  /* Space for fixed buttons */
        }
        .stButton > button {
            height: 60px;
            margin: 0 5px;
            font-size: 16px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Main content div
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Create two columns for image and analysis
    image_col, analysis_col = st.columns([2, 1])
    
    # Show image in left column
    with image_col:
        with open(filepath, 'r') as f:
            svg_content = f.read()
        st.image(filepath)
    
    # Show analysis in right column
    with analysis_col:
        if auto_categorize:
            # Get or calculate analysis results
            if 'current_analysis' not in st.session_state:
                scores = st.session_state.analyzer.analyze_svg(svg_content)
                suggested_category, confidence = st.session_state.analyzer.suggest_category(svg_content)
                st.session_state.current_analysis = {
                    'scores': scores,
                    'suggested_category': suggested_category,
                    'confidence': confidence
                }
            else:
                scores = st.session_state.current_analysis['scores']
                suggested_category = st.session_state.current_analysis['suggested_category']
                confidence = st.session_state.current_analysis['confidence']
            
            st.markdown("### Analyse Resultaten")
            
            # Create a container with custom styling for the analysis results
            analysis_container = st.container()
            with analysis_container:
                st.markdown("""
                    <style>
                    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
                        background-color: #f0f2f6;
                        padding: 1rem;
                        border-radius: 0.5rem;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                # Suggested category and confidence
                st.info(f"**Voorgestelde categorie:** {suggested_category}")
                st.progress(confidence, text=f"Betrouwbaarheid: {confidence:.1%}")
                
                # Show detailed scores in an expander
                with st.expander("Bekijk alle scores", expanded=True):
                    for cat_name, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                        st.progress(score, text=f"{cat_name}: {score:.1%}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Category selection buttons with shortcuts in fixed container
    st.markdown('<div class="category-buttons">', unsafe_allow_html=True)
    
    # Calculate button width based on number of categories
    num_categories = len(st.session_state.categories)
    button_width = min(90/num_categories, 30)  # Max width of 30% per button
    
    # Create single row of buttons
    cols = st.columns(num_categories)
    for i, (cat_id, category) in enumerate(sorted(st.session_state.categories.items(), key=lambda x: x[1].name)):
        with cols[i]:
            # Add shortcut number (1-9) if within first 9 categories
            shortcut = f"[{i+1}] " if i < 9 else ""
            if st.button(f"{shortcut}{category.name}", key=f"btn_{cat_id}_{current_file}", use_container_width=True):
                scores = st.session_state.analyzer.analyze_svg(svg_content) if auto_categorize else None
                save_categorization(current_file, cat_id, scores)
                st.success(f"Bestand gecategoriseerd als: {category.name}")
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add keyboard shortcuts using Streamlit components
    components.html(
        """
        <script>
        function handleKeyPress(event) {
            // Handle number keys for categories
            if (event.key >= '1' && event.key <= '9') {
                const allButtons = Array.from(window.parent.document.querySelectorAll('.stButton > button'));
                const categoryButtons = allButtons.filter(btn => btn.textContent.includes('['));
                const index = parseInt(event.key) - 1;
                
                if (index < categoryButtons.length) {
                    categoryButtons[index].click();
                }
            }
            // Handle arrow keys for navigation
            else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                const allButtons = Array.from(window.parent.document.querySelectorAll('.stButton > button'));
                const navButton = allButtons.find(btn => 
                    (event.key === 'ArrowLeft' && btn.textContent === '⬅️') ||
                    (event.key === 'ArrowRight' && btn.textContent === '➡️')
                );
                
                if (navButton && !navButton.disabled) {
                    navButton.click();
                }
            }
        }
        
        // Remove any existing event listener
        window.parent.document.removeEventListener('keydown', handleKeyPress);
        // Add the event listener
        window.parent.document.addEventListener('keydown', handleKeyPress);
        </script>
        """,
        height=0,
    )

def show_category_keywords(category):
    """Show and edit keywords for a category"""
    st.write("Steekwoorden:")
    
    # Show current keywords
    for i, keyword in enumerate(category.keywords):
        cols = st.columns([3, 1])
        # Show keyword with delete button
        cols[0].text(keyword)
        if cols[1].button("🗑️", key=f"del_keyword_{category.id}_{i}"):
            category.keywords.remove(keyword)
            save_categories(st.session_state.categories)
            st.rerun()
    
    # Add new keyword
    new_keyword = st.text_input("Nieuw steekwoord", key=f"new_keyword_{category.id}")
    if st.button("Toevoegen", key=f"add_keyword_{category.id}") and new_keyword:
        if new_keyword not in category.keywords:
            category.keywords.append(new_keyword)
            save_categories(st.session_state.categories)
            st.rerun()
        else:
            st.error("Dit steekwoord bestaat al")

def main():
    st.title("SVG File Categorizer 🏷️")
    
    # Get file counts for tabs
    uncategorized_files = get_uncategorized_files()
    categorized_files = load_categorization()
    uncategorized_count = len(uncategorized_files)
    categorized_count = len(categorized_files)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Instellingen")
        
        # Auto-categorization settings
        st.subheader("Automatische Analyse")
        auto_categorize = st.checkbox("Automatisch analyseren", value=True)
        confidence_threshold = st.slider(
            "Betrouwbaarheidsdrempel",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            help="Minimale betrouwbaarheidsscore voor automatische categorisatie"
        )
        
        # Category management
        st.subheader("Categorieën Beheer")
        
        # Add new category
        new_category = st.text_input("Voeg nieuwe categorie toe")
        if st.button("Categorie Toevoegen") and new_category:
            category_id = str(uuid.uuid4())
            st.session_state.categories[category_id] = Category(category_id, new_category, [])
            save_categories(st.session_state.categories)
            st.success(f"Categorie toegevoegd: {new_category}")
        
        # List and manage existing categories
        st.write("### Huidige Categorieën")
        for cat_id, category in sorted(st.session_state.categories.items(), key=lambda x: x[1].name):
            with st.expander(category.name):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                # Show category name or edit field
                if st.session_state.editing_category == cat_id:
                    new_name = col1.text_input("Nieuwe naam", category.name, key=f"edit_{cat_id}")
                    if col2.button("Opslaan", key=f"save_{cat_id}"):
                        category.name = new_name
                        save_categories(st.session_state.categories)
                        st.session_state.editing_category = None
                        st.rerun()
                else:
                    col1.write(category.name)
                    if col2.button("✏️", key=f"edit_{cat_id}"):
                        st.session_state.editing_category = cat_id
                
                # Delete button
                if col3.button("🗑️", key=f"delete_{cat_id}"):
                    if len(st.session_state.categories) > 1:  # Prevent deleting all categories
                        del st.session_state.categories[cat_id]
                        save_categories(st.session_state.categories)
                        st.rerun()
                    else:
                        st.error("Kan niet alle categorieën verwijderen")
                
                # Show and edit keywords
                show_category_keywords(category)
    
    # Main content
    tab1, tab2, tab3 = st.tabs([
        f"Categoriseren ({uncategorized_count})", 
        "Upload Bestanden",
        f"Gecategoriseerde Afbeeldingen ({categorized_count})"
    ])
    
    with tab1:
        st.header("Categoriseer Afbeeldingen")
        show_next_uncategorized_file(auto_categorize, confidence_threshold)
    
    with tab2:
        st.header("Upload Nieuwe Bestanden")
        uploaded_files = st.file_uploader("Upload SVG bestanden", type=['svg'], accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Save uploaded file to images directory
                save_path = os.path.join(DEFAULT_IMAGES_DIR, uploaded_file.name)
                with open(save_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
            st.success(f"{len(uploaded_files)} bestand(en) geüpload naar {DEFAULT_IMAGES_DIR}")
            st.rerun()
    
    with tab3:
        st.header("Gecategoriseerde Afbeeldingen")
        show_categorized_files()

if __name__ == "__main__":
    main() 