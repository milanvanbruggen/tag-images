import streamlit as st
import os
import json
from pathlib import Path
import streamlit.components.v1 as components
import datetime

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
    {"label": "3 cutouts", "value": 3},
    {"label": "Multiple/complex cutouts", "value": -1}  # Special value for complex cutouts
]

# Add custom CSS at the top of the app
st.markdown("""
<style>
    /* Navigation container */
    div[data-testid="column"] > div:has(button:contains("Previous")),
    div[data-testid="column"] > div:has(button:contains("Next")) {
        padding: 0 10px;
    }
    
    /* Navigation buttons */
    div[data-testid="column"] button:contains("Previous"), 
    div[data-testid="column"] button:contains("Next") {
        width: 100%;
        background-color: white;
        border: 1px solid #ddd;
        padding: 0.5rem;
        border-radius: 0.3rem;
        display: inline-flex !important;
        align-items: center;
        justify-content: center;
    }
    
    div[data-testid="column"] button:contains("Previous")::before {
        content: "←";
        margin-right: 0.5rem;
    }
    
    div[data-testid="column"] button:contains("Next")::after {
        content: "→";
        margin-left: 0.5rem;
    }
    
    /* Image counter */
    div[data-testid="column"]:has(> div > p:contains("Image")) {
        text-align: right;
    }
    
    div[data-testid="column"] p:contains("Image") {
        color: #666;
        margin: 0;
    }
    
    /* Hide default Streamlit buttons */
    div[data-testid="stVerticalBlock"] > div.element-container:has(.typing-button-container) + div.element-container {
        display: none !important;
        position: absolute !important;
        pointer-events: none !important;
        opacity: 0 !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    
    /* Position typing buttons */
    .typing-button-container {
        width: 100%;
        margin-bottom: 10px;
    }
    
    /* Option buttons */
    .option-button {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 0.75rem;
        width: 100%;
        font-size: 1.1em;
        line-height: 1.5;
        color: #333;
        transition: all 0.2s;
        cursor: pointer;
        text-align: left;
        display: flex;
        align-items: center;
    }
    
    .option-button:hover {
        background-color: #e9ecef;
        border-color: #ced4da;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .option-button:active {
        background-color: #e9ecef;
        transform: translateY(0);
        box-shadow: none;
    }
    
    /* Add styles for the clicked state */
    .option-button[data-clicked="true"] {
        background-color: #e9ecef;
        border-color: #ced4da;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* Number badges */
    span.number-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: white;
        color: #666;
        border: 1px solid #dee2e6;
        border-radius: 50%;
        width: 1.8em;
        height: 1.8em;
        margin-right: 0.75rem;
        font-size: 0.9em;
        flex-shrink: 0;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

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
    # Add typing date to results
    results['typed_date'] = datetime.datetime.now().isoformat()
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
    # Get untyped files or the file being edited
    if hasattr(st.session_state, 'editing_file'):
        files = [st.session_state.editing_file]
        is_editing = True
    else:
        files = get_untyped_files()
        is_editing = False

    if not files:
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
        if is_editing:
            st.write("Editing mode")
        nav_col1, nav_col2, _ = st.columns([1, 1, 8])
        with nav_col1:
            if st.button("Previous", disabled=st.session_state.current_file_index == 0, key="prev_btn"):
                st.session_state.current_file_index = max(0, st.session_state.current_file_index - 1)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                st.rerun()
        
        with nav_col2:
            if st.button("Next", disabled=st.session_state.current_file_index == len(files) - 1, key="next_btn"):
                st.session_state.current_file_index = min(len(files) - 1, st.session_state.current_file_index + 1)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                st.rerun()
    
    with col2:
        if not is_editing:
            st.write(f"Image {st.session_state.current_file_index + 1} of {len(files)}")
    
    # Current file
    current_file = files[st.session_state.current_file_index]
    filepath = os.path.join(DEFAULT_IMAGES_DIR, current_file)
    if is_editing:
        st.caption(f"Editing: {current_file}")
    else:
        st.caption(f"Typing: {current_file}")
    
    # Calculate overall progress
    total_steps = 3  # basic_shape, number_of_cutouts, drill_holes
    current_progress = 0
    
    if 'current_step' in st.session_state:
        if st.session_state.current_step == 'basic_shape':
            current_progress = 0
        elif st.session_state.current_step == 'number_of_cutouts':
            current_progress = 1
        elif st.session_state.current_step == 'cutouts':
            # For cutouts, show partial progress between number_of_cutouts and drill_holes
            cutout_count = st.session_state.current_results.get('cutout_count', 0)
            if cutout_count > 0:
                current_cutout = getattr(st.session_state, 'current_cutout', 0)
                current_progress = 1 + (current_cutout / cutout_count)
        elif st.session_state.current_step == 'drill_holes':
            current_progress = 2
    
    # Show progress bar
    progress = current_progress / total_steps
    st.progress(progress)
    st.caption(f"Step {int(current_progress) + 1} of {total_steps}")
    
    # Create two columns for image and buttons
    img_col, btn_col = st.columns([2, 1])
    
    # Show image in left column
    with img_col:
        st.image(filepath)
    
    # Show buttons in right column
    with btn_col:
        # Show current step
        if st.session_state.current_step == 'basic_shape':
            st.subheader("Basic Shape")
            for i, shape in enumerate(BASIC_SHAPES):
                st.markdown(f'''
                    <div class="typing-button-container">
                        <button class="option-button" data-streamlit-key="{shape}">
                            <span class="number-badge">{(i+1)%10}</span>{shape}
                        </button>
                    </div>
                ''', unsafe_allow_html=True)
                if st.button("", key=shape):
                    st.session_state.current_results['basic_shape'] = shape
                    st.session_state.current_step = 'number_of_cutouts'
                    st.rerun()
        
        elif st.session_state.current_step == 'number_of_cutouts':
            st.subheader("Number of Cutouts")
            for i, count_opt in enumerate(CUTOUT_COUNTS):
                st.markdown(f'''
                    <div class="typing-button-container">
                        <button class="option-button" data-streamlit-key="{count_opt["label"]}">
                            <span class="number-badge">{(i+1)%10}</span>{count_opt["label"]}
                        </button>
                    </div>
                ''', unsafe_allow_html=True)
                if st.button("", key=count_opt["label"]):
                    st.session_state.current_results['number_of_cutouts'] = count_opt['label']
                    st.session_state.current_results['cutout_count'] = count_opt['value']
                    if count_opt['value'] == -1:  # Multiple/complex cutouts
                        st.session_state.current_step = 'drill_holes'
                    elif count_opt['value'] > 0:
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
            for i, shape in enumerate(CUTOUT_SHAPES):
                st.markdown(f'''
                    <div class="typing-button-container">
                        <button class="option-button" data-streamlit-key="{shape}">
                            <span class="number-badge">{(i+1)%10}</span>{shape}
                        </button>
                    </div>
                ''', unsafe_allow_html=True)
                if st.button("", key=shape):
                    st.session_state.current_results[f'cutout_{current_cutout}'] = shape
                    if current_cutout + 1 < cutout_count:
                        st.session_state.current_cutout = current_cutout + 1
                    else:
                        st.session_state.current_step = 'drill_holes'
                    st.rerun()
        
        elif st.session_state.current_step == 'drill_holes':
            st.subheader("Drill Holes")
            st.markdown(f'''
                <div class="typing-button-container">
                    <button class="option-button" data-streamlit-key="drill_no">
                        <span class="number-badge">1</span>No
                    </button>
                </div>
            ''', unsafe_allow_html=True)
            if st.button("", key="drill_no"):
                st.session_state.current_results['drill_holes'] = "No"
                save_typing_result(current_file, st.session_state.current_results)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                if hasattr(st.session_state, 'current_cutout'):
                    delattr(st.session_state, 'current_cutout')
                st.success("Typing saved!")
                st.rerun()
            
            st.markdown(f'''
                <div class="typing-button-container">
                    <button class="option-button" data-streamlit-key="drill_yes">
                        <span class="number-badge">2</span>Yes
                    </button>
                </div>
            ''', unsafe_allow_html=True)
            if st.button("", key="drill_yes"):
                st.session_state.current_results['drill_holes'] = "Yes"
                save_typing_result(current_file, st.session_state.current_results)
                st.session_state.current_results = {}
                st.session_state.current_step = 'basic_shape'
                if hasattr(st.session_state, 'current_cutout'):
                    delattr(st.session_state, 'current_cutout')
                st.success("Typing saved!")
                st.rerun()
    
    # Update keyboard shortcuts and click handlers
    components.html(
        """
        <script>
        function triggerStreamlitButton(key) {
            // Find the hidden Streamlit button by searching for its key in the data-testid attribute
            const buttons = Array.from(window.parent.document.querySelectorAll('button[data-testid^="baseButton-"]'));
            const hiddenButton = buttons.find(btn => {
                const container = btn.closest('div[data-testid="element-container"]');
                return container && container.previousElementSibling && 
                       container.previousElementSibling.querySelector(`[data-streamlit-key="${key}"]`);
            });
            
            if (hiddenButton) {
                hiddenButton.click();
            }
        }

        function handleKeyPress(event) {
            // Handle number keys for options (1-9)
            if (event.key >= '1' && event.key <= '9') {
                const index = parseInt(event.key) - 1;
                const buttons = Array.from(window.parent.document.querySelectorAll('.typing-button-container .option-button'));
                if (buttons[index]) {
                    // Remove clicked state from all buttons
                    buttons.forEach(btn => {
                        btn.removeAttribute('data-clicked');
                    });
                    
                    // Add clicked state to the selected button
                    buttons[index].setAttribute('data-clicked', 'true');
                    
                    const key = buttons[index].getAttribute('data-streamlit-key');
                    if (key) {
                        triggerStreamlitButton(key);
                    }
                }
            }
            // Handle arrow keys for navigation
            else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                const navButtons = Array.from(window.parent.document.querySelectorAll('button'));
                const navButton = navButtons.find(btn => 
                    (event.key === 'ArrowLeft' && btn.textContent.includes('Previous')) ||
                    (event.key === 'ArrowRight' && btn.textContent.includes('Next'))
                );
                
                if (navButton && !navButton.disabled) {
                    navButton.click();
                }
            }
        }
        
        // Remove any existing event listeners
        window.parent.document.removeEventListener('keydown', handleKeyPress);
        
        // Add the event listener for keyboard shortcuts
        window.parent.document.addEventListener('keydown', handleKeyPress);

        // Add click handlers for option buttons
        window.parent.document.querySelectorAll('.typing-button-container .option-button').forEach(button => {
            button.addEventListener('click', (e) => {
                // Remove clicked state from all buttons
                window.parent.document.querySelectorAll('.typing-button-container .option-button').forEach(btn => {
                    btn.removeAttribute('data-clicked');
                });
                
                // Add clicked state to the clicked button
                button.setAttribute('data-clicked', 'true');
                
                const key = button.getAttribute('data-streamlit-key');
                if (key) {
                    triggerStreamlitButton(key);
                }
            });
        });
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
    
    # Add search and filter controls
    col1, col2, col3 = st.columns([2, 2, 1])
    
    # Search by filename
    with col1:
        search_query = st.text_input("🔍 Search by filename", key="search_filename")
    
    # Filter by typing values
    with col2:
        filter_options = {
            'Basic Shape': BASIC_SHAPES,
            'Number of Cutouts': [opt["label"] for opt in CUTOUT_COUNTS],
            'Drill Holes': ['Yes', 'No']
        }
        selected_filter = st.selectbox("Filter by", ['None'] + list(filter_options.keys()))
        if selected_filter != 'None':
            filter_value = st.selectbox("Value", filter_options[selected_filter])
    
    # Sort options
    with col3:
        sort_by = st.selectbox("Sort by", ['Filename (A-Z)', 'Filename (Z-A)', 'Last Typed Date', 'First Typed Date'])
    
    # Filter and sort results
    filtered_items = []
    for filename, results in typed.items():
        # Apply filename search
        if search_query and search_query.lower() not in filename.lower():
            continue
        
        # Apply type filter
        if selected_filter != 'None':
            if selected_filter == 'Basic Shape' and results.get('basic_shape') != filter_value:
                continue
            elif selected_filter == 'Number of Cutouts' and results.get('number_of_cutouts') != filter_value:
                continue
            elif selected_filter == 'Drill Holes' and results.get('drill_holes') != filter_value:
                continue
        
        # Add to filtered list with metadata
        filtered_items.append({
            'filename': filename,
            'results': results,
            'typed_date': results.get('typed_date', '1970-01-01T00:00:00')  # Default date for old entries
        })
    
    # Sort items
    if sort_by == 'Filename (A-Z)':
        filtered_items.sort(key=lambda x: x['filename'])
    elif sort_by == 'Filename (Z-A)':
        filtered_items.sort(key=lambda x: x['filename'], reverse=True)
    elif sort_by == 'Last Typed Date':
        filtered_items.sort(key=lambda x: x['typed_date'], reverse=True)
    elif sort_by == 'First Typed Date':
        filtered_items.sort(key=lambda x: x['typed_date'])
    
    # Show results count
    st.caption(f"Showing {len(filtered_items)} of {len(typed)} items")
    
    # Display filtered and sorted results
    for item in filtered_items:
        filename = item['filename']
        results = item['results']
        
        # Format the typing date for display
        typed_date = results.get('typed_date', 'Unknown date')
        if typed_date != 'Unknown date':
            try:
                date_obj = datetime.datetime.fromisoformat(typed_date)
                typed_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        with st.expander(f"{filename} (Typed: {typed_date})"):
            filepath = os.path.join(DEFAULT_IMAGES_DIR, filename)
            if os.path.exists(filepath):
                col1, col2 = st.columns([1, 3])
                col1.image(filepath, width=100)
                
                # Show editable results
                edited = False
                updated_results = results.copy()
                
                # Basic Shape
                current_shape = results.get('basic_shape', '')
                new_shape = col2.selectbox(
                    "Basic Shape",
                    BASIC_SHAPES,
                    index=BASIC_SHAPES.index(current_shape) if current_shape in BASIC_SHAPES else 0,
                    key=f"basic_shape_{filename}"
                )
                if new_shape != current_shape:
                    updated_results['basic_shape'] = new_shape
                    edited = True
                
                # Number of Cutouts
                current_cutouts = results.get('number_of_cutouts', '')
                cutout_options = [opt["label"] for opt in CUTOUT_COUNTS]
                new_cutouts = col2.selectbox(
                    "Number of Cutouts",
                    cutout_options,
                    index=cutout_options.index(current_cutouts) if current_cutouts in cutout_options else 0,
                    key=f"cutouts_{filename}"
                )
                if new_cutouts != current_cutouts:
                    updated_results['number_of_cutouts'] = new_cutouts
                    # Update the cutout count value
                    for opt in CUTOUT_COUNTS:
                        if opt["label"] == new_cutouts:
                            updated_results['cutout_count'] = opt["value"]
                            break
                    edited = True
                
                # Individual Cutouts
                cutout_count = updated_results.get('cutout_count', 0)
                for i in range(cutout_count):
                    current_cutout = results.get(f'cutout_{i}', '')
                    new_cutout = col2.selectbox(
                        f"Cutout {i+1}",
                        CUTOUT_SHAPES,
                        index=CUTOUT_SHAPES.index(current_cutout) if current_cutout in CUTOUT_SHAPES else 0,
                        key=f"cutout_{i}_{filename}"
                    )
                    if new_cutout != current_cutout:
                        updated_results[f'cutout_{i}'] = new_cutout
                        edited = True
                
                # Drill Holes
                current_drill = results.get('drill_holes', '')
                new_drill = col2.selectbox(
                    "Drill Holes",
                    ["No", "Yes"],
                    index=1 if current_drill == "Yes" else 0,
                    key=f"drill_{filename}"
                )
                if new_drill != current_drill:
                    updated_results['drill_holes'] = new_drill
                    edited = True
                
                # Save changes if edited
                if edited:
                    save_typing_result(filename, updated_results)
                    st.success("Changes saved!")
                
                # Delete button
                if col2.button("🗑️ Delete", key=f"delete_{filename}"):
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