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
    page_title="SVG Typering",
    page_icon="🏷️",
    layout="wide"
)

# Constants for file paths
DEFAULT_IMAGES_DIR = "images"
TYPING_CONFIG_FILE = "typing_config.json"
TYPING_RESULTS_FILE = "typed_images.json"

class TypingStep:
    def __init__(self, id, name, options, order=None):
        self.id = id
        self.name = name
        self.options = options if isinstance(options, list) else []
        self.order = order
        # Initialize option orders if not present
        if not all(isinstance(opt, dict) for opt in self.options):
            self.options = [{'value': opt, 'order': i} for i, opt in enumerate(self.options)]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'options': self.options,
            'order': self.order
        }

    @staticmethod
    def from_dict(data):
        return TypingStep(data['id'], data['name'], data['options'], data.get('order'))

    def get_ordered_options(self):
        """Get options sorted by order"""
        return [opt['value'] for opt in sorted(self.options, key=lambda x: x['order'])]

    def get_option_by_value(self, value):
        """Get option dict by value"""
        return next((opt for opt in self.options if opt['value'] == value), None)

def load_typing_config():
    """Load typing configuration from JSON file"""
    if os.path.exists(TYPING_CONFIG_FILE):
        with open(TYPING_CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
            steps = {step['id']: TypingStep.from_dict(step) for step in config_data}
            
            # Ensure all steps have an order
            if any(step.order is None for step in steps.values()):
                for i, step in enumerate(steps.values()):
                    step.order = i
                save_typing_config(steps)
            
            return steps
    
    # Default typing steps with order
    default_steps = {
        'basic_shape': TypingStep('basic_shape', 'Basisvorm', [
            'Vierhoek', 'Rond', 'Driehoek', 'Tekst', 'Custom vorm'
        ], 0),
        'cutout': TypingStep('cutout', 'Uitsparing', [
            'Niet van toepassing', 'Vierhoek', 'Rond', 'Driehoek', 'Tekst', 'Custom vorm'
        ], 1),
        'drill_holes': TypingStep('drill_holes', 'Boorgaten', [
            'Ja', 'Nee'
        ], 2),
        'rounded_corners': TypingStep('rounded_corners', 'Afgeronde hoeken', [
            'Ja', 'Nee'
        ], 3)
    }
    save_typing_config(default_steps)
    return default_steps

def save_typing_config(config):
    """Save typing configuration to JSON file"""
    config_data = [step.to_dict() for step in config.values()]
    with open(TYPING_CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

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
    data[filename] = {
        'results': results,
        'timestamp': str(pd.Timestamp.now())
    }
    with open(TYPING_RESULTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_untyped_files():
    """Get list of untyped SVG files"""
    if not os.path.exists(DEFAULT_IMAGES_DIR):
        os.makedirs(DEFAULT_IMAGES_DIR)
    
    typed = load_typing_results()
    all_files = [f for f in os.listdir(DEFAULT_IMAGES_DIR) if f.lower().endswith('.svg')]
    return [f for f in all_files if f not in typed]

# Initialize session state
if 'typing_steps' not in st.session_state:
    st.session_state.typing_steps = load_typing_config()
if 'current_file_index' not in st.session_state:
    st.session_state.current_file_index = 0
if 'current_step' not in st.session_state:
    st.session_state.current_step = list(st.session_state.typing_steps.keys())[0]
if 'current_results' not in st.session_state:
    st.session_state.current_results = {}

def show_typing_config():
    """Show and edit typing configuration"""
    st.header("Typering Configuratie")
    
    # Add new step
    new_step_name = st.text_input("Nieuwe stap toevoegen")
    if st.button("Stap Toevoegen") and new_step_name:
        step_id = str(uuid.uuid4())
        max_order = max((step.order for step in st.session_state.typing_steps.values()), default=-1)
        st.session_state.typing_steps[step_id] = TypingStep(step_id, new_step_name, [], max_order + 1)
        save_typing_config(st.session_state.typing_steps)
        st.success(f"Stap toegevoegd: {new_step_name}")
        st.rerun()
    
    # Sort steps by order
    sorted_steps = sorted(st.session_state.typing_steps.items(), key=lambda x: x[1].order)
    
    # Edit existing steps
    for step_id, step in sorted_steps:
        with st.expander(step.name):
            cols = st.columns([3, 1, 1])
            
            # Move step up/down buttons
            with cols[1]:
                if st.button("⬆️", key=f"up_step_{step_id}", disabled=step.order == 0):
                    for other_id, other_step in st.session_state.typing_steps.items():
                        if other_step.order == step.order - 1:
                            step.order, other_step.order = other_step.order, step.order
                            save_typing_config(st.session_state.typing_steps)
                            st.rerun()
                            break
            
            with cols[2]:
                if st.button("⬇️", key=f"down_step_{step_id}", disabled=step.order == len(sorted_steps) - 1):
                    for other_id, other_step in st.session_state.typing_steps.items():
                        if other_step.order == step.order + 1:
                            step.order, other_step.order = other_step.order, step.order
                            save_typing_config(st.session_state.typing_steps)
                            st.rerun()
                            break
            
            # Edit step name
            new_name = st.text_input("Naam", step.name, key=f"name_step_{step_id}")
            if new_name != step.name:
                step.name = new_name
                save_typing_config(st.session_state.typing_steps)
            
            # Edit options
            st.write("Opties:")
            for option in sorted(step.options, key=lambda x: x['order']):
                option_id = f"{step_id}_{option['order']}"
                cols = st.columns([3, 1, 1, 1])
                
                # Option name with edit functionality
                old_value = option['value']
                new_value = cols[0].text_input(
                    "Optie",  # Add a label to prevent warning
                    old_value,
                    key=f"option_value_{option_id}",
                    label_visibility="collapsed"  # Hide the label
                )
                if new_value != old_value:
                    # Update option value
                    option['value'] = new_value
                    save_typing_config(st.session_state.typing_steps)
                    
                    # Update existing results that use this option
                    typed_files = load_typing_results()
                    modified = False
                    for file_data in typed_files.values():
                        results = file_data['results']
                        if step_id in results and results[step_id] == old_value:
                            results[step_id] = new_value
                            modified = True
                    
                    if modified:
                        with open(TYPING_RESULTS_FILE, 'w') as f:
                            json.dump(typed_files, f, indent=4)
                    
                    st.rerun()
                
                # Move option up
                if cols[1].button("⬆️", key=f"up_opt_{option_id}", 
                                disabled=option['order'] == 0):
                    for other_opt in step.options:
                        if other_opt['order'] == option['order'] - 1:
                            option['order'], other_opt['order'] = other_opt['order'], option['order']
                            save_typing_config(st.session_state.typing_steps)
                            st.rerun()
                            break
                
                # Move option down
                if cols[2].button("⬇️", key=f"down_opt_{option_id}", 
                                disabled=option['order'] == len(step.options) - 1):
                    for other_opt in step.options:
                        if other_opt['order'] == option['order'] + 1:
                            option['order'], other_opt['order'] = other_opt['order'], option['order']
                            save_typing_config(st.session_state.typing_steps)
                            st.rerun()
                            break
                
                # Delete option
                if cols[3].button("🗑️", key=f"del_opt_{option_id}"):
                    deleted_order = option['order']
                    step.options = [opt for opt in step.options if opt['order'] != deleted_order]
                    # Reorder remaining options
                    for opt in step.options:
                        if opt['order'] > deleted_order:
                            opt['order'] -= 1
                    save_typing_config(st.session_state.typing_steps)
                    st.rerun()
            
            # Add new option
            new_option = st.text_input("Nieuwe optie", key=f"new_option_step_{step_id}")
            if st.button("Optie Toevoegen", key=f"add_option_step_{step_id}") and new_option:
                if not any(opt['value'] == new_option for opt in step.options):
                    max_order = max((opt['order'] for opt in step.options), default=-1)
                    step.options.append({'value': new_option, 'order': max_order + 1})
                    save_typing_config(st.session_state.typing_steps)
                    st.rerun()
                else:
                    st.error("Deze optie bestaat al")
            
            # Delete step
            if st.button("Stap Verwijderen", key=f"del_step_{step_id}"):
                if len(st.session_state.typing_steps) > 1:
                    deleted_order = step.order
                    del st.session_state.typing_steps[step_id]
                    for other_step in st.session_state.typing_steps.values():
                        if other_step.order > deleted_order:
                            other_step.order -= 1
                    save_typing_config(st.session_state.typing_steps)
                    st.rerun()
                else:
                    st.error("Kan niet alle stappen verwijderen")

def show_next_untyped_file():
    """Show and process the next untyped file"""
    untyped = get_untyped_files()
    if not untyped:
        st.info(f"Geen ongetypeerde bestanden gevonden in {DEFAULT_IMAGES_DIR}")
        st.write(f"Plaats SVG bestanden in de '{DEFAULT_IMAGES_DIR}' map om ze te typeren")
        return

    # Navigation and file info
    nav_container = st.container()
    with nav_container:
        st.markdown("""
            <style>
            [data-testid="stVerticalBlock"] > div:has(button:contains("⬅️")) {
                background-color: #f0f2f6;
                padding: 0.5rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Navigation row
        nav_col1, nav_col2 = st.columns([8, 2])
        
        with nav_col1:
            nav_buttons_col1, nav_buttons_col2, nav_buttons_col3 = st.columns([1, 1, 18])
            with nav_buttons_col1:
                if st.button("⬅️", disabled=st.session_state.current_file_index == 0):
                    st.session_state.current_file_index = max(0, st.session_state.current_file_index - 1)
                    st.session_state.current_results = {}
                    st.session_state.current_step = list(st.session_state.typing_steps.keys())[0]
                    st.rerun()
            with nav_buttons_col2:
                if st.button("➡️", disabled=st.session_state.current_file_index == len(untyped) - 1):
                    st.session_state.current_file_index = min(len(untyped) - 1, st.session_state.current_file_index + 1)
                    st.session_state.current_results = {}
                    st.session_state.current_step = list(st.session_state.typing_steps.keys())[0]
                    st.rerun()
        
        with nav_col2:
            st.write(f"Afbeelding {st.session_state.current_file_index + 1} van {len(untyped)}")
        
        current_file = untyped[st.session_state.current_file_index]
        filepath = os.path.join(DEFAULT_IMAGES_DIR, current_file)
        st.caption(f"Typeren: {current_file}")
    
    # Show current step and options
    current_step = st.session_state.typing_steps[st.session_state.current_step]
    st.subheader(current_step.name)
    
    # Create columns for options
    ordered_options = current_step.get_ordered_options()
    cols = st.columns(len(ordered_options))
    for i, option_value in enumerate(ordered_options):
        with cols[i]:
            # Add number prefix for keyboard shortcut
            button_label = f"[{i+1}] {option_value}"
            if st.button(button_label, key=f"option_{current_step.id}_{i}", use_container_width=True):
                st.session_state.current_results[current_step.id] = option_value
                
                # Move to next step or save results
                sorted_steps = sorted(st.session_state.typing_steps.items(), key=lambda x: x[1].order)
                current_index = next(i for i, (step_id, _) in enumerate(sorted_steps) if step_id == st.session_state.current_step)
                
                if current_index < len(sorted_steps) - 1:
                    st.session_state.current_step = sorted_steps[current_index + 1][0]
                else:
                    save_typing_result(current_file, st.session_state.current_results)
                    st.session_state.current_results = {}
                    st.session_state.current_step = sorted_steps[0][0]
                    st.success("Typering opgeslagen!")
                st.rerun()
    
    # Add some spacing
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    
    # Show image
    with open(filepath, 'r') as f:
        svg_content = f.read()
    st.image(filepath)
    
    # Add keyboard shortcuts
    components.html(
        """
        <script>
        function handleKeyPress(event) {
            // Handle number keys for options (1-9)
            if (event.key >= '1' && event.key <= '9') {
                const allButtons = Array.from(window.parent.document.querySelectorAll('.stButton > button'));
                const optionButtons = allButtons.filter(btn => btn.textContent.includes('[' + event.key + ']'));
                if (optionButtons.length > 0) {
                    optionButtons[0].click();
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

def show_typed_files():
    """Show overview of typed files"""
    typed = load_typing_results()
    if not typed:
        st.info("Nog geen bestanden getypeerd")
        return
    
    # Sort steps by order for consistent display
    sorted_steps = sorted(st.session_state.typing_steps.items(), key=lambda x: x[1].order)
    
    for filename, data in sorted(typed.items()):
        with st.expander(filename):
            col1, col2, col3 = st.columns([2, 3, 1])
            
            filepath = os.path.join(DEFAULT_IMAGES_DIR, filename)
            if os.path.exists(filepath):
                col1.image(filepath, width=100)
                
                # Show results with dropdowns
                results = data['results']
                modified = False
                
                for step_id, step in sorted_steps:
                    current_value = results.get(step_id, "Niet ingevuld")
                    
                    # Create dropdown with all options plus "Niet ingevuld"
                    options = ["Niet ingevuld"] + step.get_ordered_options()
                    
                    # Handle case where current value is not in options anymore
                    if current_value not in options:
                        current_value = "Niet ingevuld"
                        if step_id in results:
                            del results[step_id]
                            modified = True
                    
                    new_value = col2.selectbox(
                        step.name,
                        options=options,
                        index=options.index(current_value),
                        key=f"select_{filename}_{step_id}"
                    )
                    
                    # Update results if value changed
                    if new_value != current_value:
                        if new_value == "Niet ingevuld":
                            if step_id in results:
                                del results[step_id]
                        else:
                            results[step_id] = new_value
                        modified = True
                
                # Save if any values were modified
                if modified:
                    typed[filename]['results'] = results
                    with open(TYPING_RESULTS_FILE, 'w') as f:
                        json.dump(typed, f, indent=4)
                
                # Add remove button
                if col3.button("🗑️", key=f"remove_{filename}"):
                    del typed[filename]
                    with open(TYPING_RESULTS_FILE, 'w') as f:
                        json.dump(typed, f, indent=4)
                    st.rerun()

def main():
    st.title("SVG Typering 🏷️")
    
    # Get file counts
    untyped_files = get_untyped_files()
    typed_files = load_typing_results()
    untyped_count = len(untyped_files)
    typed_count = len(typed_files)
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs([
        f"Typeren ({untyped_count})", 
        "Upload Bestanden",
        f"Getypeerde Afbeeldingen ({typed_count})",
        "Typering Configuratie"
    ])
    
    with tab1:
        show_next_untyped_file()
    
    with tab2:
        st.header("Upload Nieuwe Bestanden")
        uploaded_files = st.file_uploader("Upload SVG bestanden", type=['svg'], accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                save_path = os.path.join(DEFAULT_IMAGES_DIR, uploaded_file.name)
                with open(save_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
            st.success(f"{len(uploaded_files)} bestand(en) geüpload naar {DEFAULT_IMAGES_DIR}")
            st.rerun()
    
    with tab3:
        st.header("Getypeerde Afbeeldingen")
        show_typed_files()
    
    with tab4:
        show_typing_config()

if __name__ == "__main__":
    main() 