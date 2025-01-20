import streamlit as st
import os
import json
from pathlib import Path
import streamlit.components.v1 as components

# Set page config
st.set_page_config(
    page_title="SVG Typing",
    page_icon="🏷️",
    layout="wide"
)

# Constants
DEFAULT_IMAGES_DIR = "images"
TYPING_RESULTS_FILE = "typed_images.json"

# Fixed options
BASIC_SHAPES = [
    "Rectangle",
    "Circle",
    "Rounded Rectangle",
    "Arched Rectangle",
    "Sloped Rectangle",
    "Trapezoid",
    "Right Angled Triangle",
    "Ellipse",
    "Text",
    "Other Shape"
]

CUTOUT_SHAPES = [
    "Rectangle",
    "Circle",
    "Rounded Rectangle",
    "Arched Rectangle",
    "Sloped Rectangle",
    "Trapezoid",
    "Right Angled Triangle",
    "Ellipse",
    "Text",
    "Other Shape"
]

CUTOUT_COUNTS = [
    {"label": "No cutouts", "value": 0},
    {"label": "1 cutout", "value": 1},
    {"label": "2 cutouts", "value": 2},
    {"label": "3 cutouts", "value": 3}
]

def load_typing_results():
    """Load typing results from JSON file"""
    if os.path.exists(TYPING_RESULTS_FILE):
        try:
            with open(TYPING_RESULTS_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except json.JSONDecodeError:
            pass
    return {}

def save_typing_result(filename, results):
    """Save typing results for a file"""
    data = load_typing_results()
    data[filename] = results
    with open(TYPING_RESULTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_untyped_files():
    """Get list of untyped SVG files"""
    if not os.path.exists(DEFAULT_IMAGES_DIR):
        os.makedirs(DEFAULT_IMAGES_DIR)
    
    typed = load_typing_results()
    all_files = [f for f in os.listdir(DEFAULT_IMAGES_DIR) if f.lower().endswith('.svg')]
    return [f for f in all_files if f not in typed]

def show_typing_interface():
    """Show the main typing interface"""
    # Get untyped files
    untyped = get_untyped_files()
    if not untyped:
        st.info(f"No untyped files found in {DEFAULT_IMAGES_DIR}")
        st.write(f"Place SVG files in the '{DEFAULT_IMAGES_DIR}' folder to type them")
        return

    # Initialize session state
    if 'current_file_index' not in st.session_state:
        st.session_state.current_file_index = 0
    if 'current_results' not in st.session_state:
        st.session_state.current_results = {}
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'basic_shape'
    
    # Navigation
    col1, col2 = st.columns([8, 2])
    with col1:
        nav_col1, nav_col2, _ = st.columns([1, 1, 8])
        with nav_col1:
            if st.button("⬅️", disabled=st.session_state.current_file_index == 0):
                st.session_state.current_file_index = max(0, st.session_state.current_file_index - 1)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                st.rerun()
        with nav_col2:
            if st.button("➡️", disabled=st.session_state.current_file_index == len(untyped) - 1):
                st.session_state.current_file_index = min(len(untyped) - 1, st.session_state.current_file_index + 1)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                st.rerun()
    
    with col2:
        st.write(f"Image {st.session_state.current_file_index + 1} of {len(untyped)}")
    
    # Current file
    current_file = untyped[st.session_state.current_file_index]
    filepath = os.path.join(DEFAULT_IMAGES_DIR, current_file)
    st.caption(f"Typing: {current_file}")
    
    # Show current step
    if st.session_state.current_step == 'basic_shape':
        st.subheader("Basic Shape")
        cols = st.columns(len(BASIC_SHAPES))
        for i, shape in enumerate(BASIC_SHAPES):
            with cols[i]:
                if st.button(f"[{i+1}] {shape}", use_container_width=True):
                    st.session_state.current_results['basic_shape'] = shape
                    st.session_state.current_step = 'number_of_cutouts'
                    st.rerun()
    
    elif st.session_state.current_step == 'number_of_cutouts':
        st.subheader("Number of Cutouts")
        cols = st.columns(len(CUTOUT_COUNTS))
        for i, count_opt in enumerate(CUTOUT_COUNTS):
            with cols[i]:
                if st.button(f"[{i+1}] {count_opt['label']}", use_container_width=True):
                    st.session_state.current_results['number_of_cutouts'] = count_opt['label']
                    st.session_state.current_results['cutout_count'] = count_opt['value']
                    if count_opt['value'] > 0:
                        st.session_state.current_step = 'cutouts'
                        st.session_state.current_cutout = 0
                    else:
                        st.session_state.current_step = 'drill_holes'
                    st.rerun()
    
    elif st.session_state.current_step == 'cutouts':
        cutout_count = st.session_state.current_results['cutout_count']
        current_cutout = getattr(st.session_state, 'current_cutout', 0)
        
        # Show progress
        progress = current_cutout / cutout_count
        st.progress(progress)
        st.caption(f"Cutout {current_cutout + 1} of {cutout_count}")
        
        # Show cutout selection
        st.subheader(f"Cutout {current_cutout + 1}")
        cols = st.columns(len(CUTOUT_SHAPES))
        for i, shape in enumerate(CUTOUT_SHAPES):
            with cols[i]:
                if st.button(f"[{i+1}] {shape}", use_container_width=True):
                    st.session_state.current_results[f'cutout_{current_cutout}'] = shape
                    if current_cutout + 1 < cutout_count:
                        st.session_state.current_cutout = current_cutout + 1
                    else:
                        st.session_state.current_step = 'drill_holes'
                    st.rerun()
    
    elif st.session_state.current_step == 'drill_holes':
        st.subheader("Drill Holes")
        col1, col2, *rest = st.columns(10)
        with col1:
            if st.button("[1] No", use_container_width=True):
                st.session_state.current_results['drill_holes'] = "No"
                save_typing_result(current_file, st.session_state.current_results)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                if hasattr(st.session_state, 'current_cutout'):
                    delattr(st.session_state, 'current_cutout')
                st.success("Typing saved!")
                st.rerun()
        with col2:
            if st.button("[2] Yes", use_container_width=True):
                st.session_state.current_results['drill_holes'] = "Yes"
                save_typing_result(current_file, st.session_state.current_results)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                if hasattr(st.session_state, 'current_cutout'):
                    delattr(st.session_state, 'current_cutout')
                st.success("Typing saved!")
                st.rerun()
    
    # Show image
    st.image(filepath)
    
    # Add keyboard shortcuts using components
    components.html(
        """
        <script>
        function handleKeyPress(event) {
            // Handle number keys for options (1-9)
            if (event.key >= '1' && event.key <= '9') {
                const allButtons = Array.from(window.parent.document.querySelectorAll('button'));
                const optionButtons = allButtons.filter(btn => btn.textContent.includes('[' + event.key + ']'));
                if (optionButtons.length > 0) {
                    optionButtons[0].click();
                }
            }
            // Handle arrow keys for navigation
            else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                const allButtons = Array.from(window.parent.document.querySelectorAll('button'));
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

def show_upload_interface():
    """Show the upload interface"""
    st.header("Upload Files")
    uploaded_files = st.file_uploader("Upload SVG files", type=['svg'], accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            save_path = os.path.join(DEFAULT_IMAGES_DIR, uploaded_file.name)
            with open(save_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
        st.success(f"{len(uploaded_files)} file(s) uploaded to {DEFAULT_IMAGES_DIR}")
        st.rerun()

def show_results_interface():
    """Show the results interface"""
    st.header("Typed Images")
    typed = load_typing_results()
    if not typed:
        st.info("No files typed yet")
        return
    
    for filename, results in typed.items():
        with st.expander(filename):
            filepath = os.path.join(DEFAULT_IMAGES_DIR, filename)
            if os.path.exists(filepath):
                col1, col2 = st.columns([1, 3])
                col1.image(filepath, width=100)
                
                # Show results
                for key, value in results.items():
                    if key != 'cutout_count':  # Skip technical fields
                        col2.write(f"{key}: {value}")
                
                # Delete button
                if col2.button("🗑️", key=f"delete_{filename}"):
                    del typed[filename]
                    with open(TYPING_RESULTS_FILE, 'w') as f:
                        json.dump(typed, f, indent=4)
                    st.rerun()

def main():
    # Get file counts
    untyped_count = len(get_untyped_files())
    typed_count = len(load_typing_results())
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        f"Type ({untyped_count})",
        "Upload Files",
        f"Typed Images ({typed_count})"
    ])
    
    with tab1:
        show_typing_interface()
    with tab2:
        show_upload_interface()
    with tab3:
        show_results_interface()

if __name__ == "__main__":
    main() 