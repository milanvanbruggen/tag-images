import streamlit as st
import os
from pathlib import Path
import shutil
import json
from svg_analyzer import SVGAnalyzer

# Set page config
st.set_page_config(
    page_title="SVG Categorizer",
    page_icon="🏷️",
    layout="wide"
)

# Initialize session state for categories if not exists
if 'categories' not in st.session_state:
    st.session_state.categories = set(['icons', 'logos', 'illustrations'])  # Default categories
if 'current_file_index' not in st.session_state:
    st.session_state.current_file_index = 0
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = SVGAnalyzer()

def save_categorization(filename, category, scores=None):
    """Save the categorization to a JSON file"""
    data = {}
    if os.path.exists('categorization.json'):
        with open('categorization.json', 'r') as f:
            data = json.load(f)
    
    data[filename] = {
        'category': category,
        'analysis_scores': scores
    }
    
    with open('categorization.json', 'w') as f:
        json.dump(data, f, indent=4)

def main():
    st.title("SVG File Categorizer 🏷️")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Settings")
        
        # Auto-categorization settings
        st.subheader("Automatische Categorisatie")
        auto_categorize = st.checkbox("Automatisch analyseren", value=True)
        confidence_threshold = st.slider(
            "Betrouwbaarheidsdrempel",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            help="Minimale betrouwbaarheidsscore voor automatische categorisatie"
        )
        
        # Category management
        st.subheader("Categorieën")
        new_category = st.text_input("Voeg nieuwe categorie toe")
        if st.button("Categorie Toevoegen") and new_category:
            st.session_state.categories.add(new_category)
            st.success(f"Categorie toegevoegd: {new_category}")
        
        st.write("Huidige categorieën:")
        for cat in sorted(st.session_state.categories):
            st.write(f"- {cat}")
    
    # Main content
    uploaded_files = st.file_uploader("Upload SVG bestanden", type=['svg'], accept_multiple_files=True)
    
    if uploaded_files:
        # Create directories if they don't exist
        for category in st.session_state.categories:
            os.makedirs(category, exist_ok=True)
        
        # Display current file
        if st.session_state.current_file_index < len(uploaded_files):
            current_file = uploaded_files[st.session_state.current_file_index]
            
            if current_file.name not in st.session_state.processed_files:
                st.subheader(f"Categoriseren: {current_file.name}")
                
                # Read and display SVG content
                svg_content = current_file.read().decode()
                st.image(current_file, use_column_width=True)
                current_file.seek(0)  # Reset file pointer
                
                # Analyze SVG if auto-categorization is enabled
                if auto_categorize:
                    scores = st.session_state.analyzer.analyze_svg(svg_content)
                    suggested_category, confidence = st.session_state.analyzer.suggest_category(svg_content)
                    
                    # Display analysis results
                    st.write("### Analyse Resultaten")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("Voorgestelde categorie:", suggested_category)
                        st.write(f"Betrouwbaarheid: {confidence:.2%}")
                    
                    with col2:
                        st.write("Scores per categorie:")
                        for cat, score in scores.items():
                            st.write(f"- {cat}: {score:.2%}")
                    
                    # Auto-categorize if confidence is high enough
                    if confidence >= confidence_threshold:
                        save_path = os.path.join(suggested_category, current_file.name)
                        with open(save_path, 'wb') as f:
                            current_file.seek(0)
                            f.write(current_file.read())
                        
                        save_categorization(current_file.name, suggested_category, scores)
                        st.session_state.processed_files.add(current_file.name)
                        st.session_state.current_file_index += 1
                        st.success(f"Automatisch gecategoriseerd als: {suggested_category}")
                        st.rerun()
                
                # Category selection buttons
                st.write("### Handmatige Categorisatie")
                cols = st.columns(len(st.session_state.categories))
                for col, category in zip(cols, sorted(st.session_state.categories)):
                    if col.button(category, key=f"btn_{category}_{current_file.name}"):
                        # Save file to category directory
                        save_path = os.path.join(category, current_file.name)
                        with open(save_path, 'wb') as f:
                            current_file.seek(0)
                            f.write(current_file.read())
                        
                        # Save categorization with analysis scores if available
                        scores = st.session_state.analyzer.analyze_svg(svg_content) if auto_categorize else None
                        save_categorization(current_file.name, category, scores)
                        
                        st.session_state.processed_files.add(current_file.name)
                        st.session_state.current_file_index += 1
                        st.rerun()
        
        # Show progress
        progress = len(st.session_state.processed_files) / len(uploaded_files)
        st.progress(progress)
        st.write(f"Verwerkt: {len(st.session_state.processed_files)} van {len(uploaded_files)} bestanden")
        
        if len(st.session_state.processed_files) == len(uploaded_files):
            st.success("Alle bestanden zijn gecategoriseerd!")
            if st.button("Opnieuw Beginnen"):
                st.session_state.current_file_index = 0
                st.session_state.processed_files = set()
                st.rerun()

if __name__ == "__main__":
    main() 