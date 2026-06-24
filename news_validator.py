import streamlit as st
import logging
import time
import os
from app import process_user_input
from dotenv import load_dotenv
from ui import templates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page config — must be first Streamlit command
st.set_page_config(
    page_title="FakeBuster",
    page_icon="ui/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load external CSS
css_path = os.path.join(os.path.dirname(__file__), "ui", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# API Key Validation
load_dotenv()
if not os.getenv('TAVILY_API_KEY') or not os.getenv('GROQ_API_KEY'):
    st.error("API Keys missing. Please set TAVILY_API_KEY and GROQ_API_KEY in your .env file.")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown(templates.get("sidebar-monogram"), unsafe_allow_html=True)
    st.markdown(templates.get("sidebar-about-heading"), unsafe_allow_html=True)
    st.markdown(templates.get("sidebar-about-body"), unsafe_allow_html=True)
    st.markdown(templates.get("sidebar-how-heading"), unsafe_allow_html=True)
    st.markdown(templates.get("sidebar-how-body"), unsafe_allow_html=True)

# --- Masthead ---
st.markdown(templates.get("masthead"), unsafe_allow_html=True)
st.markdown(templates.get("tagline"), unsafe_allow_html=True)
st.markdown(templates.get("masthead-rule-thin"), unsafe_allow_html=True)

# --- Session State ---
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""
if 'selected_time_range' not in st.session_state:
    st.session_state.selected_time_range = "month"
if 'search_depth' not in st.session_state:
    st.session_state.search_depth = "basic"


def set_example(text):
    st.session_state.user_input = text


# --- Input ---
user_input = st.text_area(
    "Enter a news headline or claim to verify:",
    value=st.session_state.user_input,
    height=100,
    placeholder="e.g., Did India successfully send a spacecraft to Mars for less than $100 million?"
)

# --- Configuration ---
col1, col2 = st.columns([1, 1])

with col1:
    time_options = ["none", "day", "week", "month", "year"]
    time_labels = ["Any Time", "Past Day", "Past Week", "Past Month", "Past Year"]
    current_index = (
        time_options.index(st.session_state.selected_time_range)
        if st.session_state.selected_time_range in time_options
        else 3
    )
    selected_time_label = st.selectbox(
        "Time Range",
        options=time_labels,
        index=current_index,
        help="Limit search results to a specific time period."
    )
    st.session_state.selected_time_range = time_options[time_labels.index(selected_time_label)]

with col2:
    depth_options = ["Quick Search", "Deep Dive"]
    current_depth_index = 0 if st.session_state.search_depth == "basic" else 1
    selected_depth_label = st.selectbox(
        "Search Depth",
        options=depth_options,
        index=current_depth_index,
        help="Quick Search is faster. Deep Dive analyzes more sources."
    )
    st.session_state.search_depth = "basic" if selected_depth_label == "Quick Search" else "advanced"

# --- Example Claims ---
st.markdown(templates.get("section-header-examples"), unsafe_allow_html=True)
st.markdown(templates.get("section-rule"), unsafe_allow_html=True)

ex_col1, ex_col2, ex_col3 = st.columns([1, 1, 1])

with ex_col1:
    st.button(
        "PM Modi and 15 lakhs",
        on_click=set_example,
        args=["Is it true that PM Modi announced 15 lakhs to every Indian citizen?"],
        help="Check this popular claim"
    )

with ex_col2:
    st.button(
        "Rahul Gandhi's MP post",
        on_click=set_example,
        args=["Did Rahul Gandhi resign his MP post recently?"],
        help="Check this political claim"
    )

with ex_col3:
    st.button(
        "India's Mars mission",
        on_click=set_example,
        args=["Did India successfully send a spacecraft to Mars for less than $100 million?"],
        help="Check this space achievement claim"
    )

# --- Verify Button ---
status = st.empty()
progress = st.empty()

if st.button("Verify This Claim", type="primary") and user_input:
    status.markdown(templates.get("status-box", message="Processing your request..."), unsafe_allow_html=True)
    progress_bar = progress.progress(0)

    for percent_complete in range(0, 51, 10):
        progress_bar.progress(percent_complete)
        if percent_complete < 50:
            time.sleep(0.1)

    try:
        max_results = 5 if st.session_state.search_depth == "basic" else 15
        with st.spinner("Analyzing information..."):
            result = process_user_input(
                user_input,
                time_range=st.session_state.selected_time_range,
                search_depth=st.session_state.search_depth,
                max_results=max_results,
                status_callback=None
            )

            if isinstance(result, dict):
                analysis_data = result.get("response", "")
                sources = result.get("sources", [])
                is_stream = result.get("is_stream", False)
            else:
                analysis_data = result
                sources = []
                is_stream = False

            for percent_complete in range(50, 101, 10):
                progress_bar.progress(percent_complete)
                if percent_complete < 100:
                    time.sleep(0.1)

            status.empty()
            progress.empty()

            # --- Verdict & Analysis Display ---
            verdict_class_map = {
                "TRUE": "verdict-true",
                "FALSE": "verdict-false",
                "PARTIALLY TRUE": "verdict-partial",
                "INSUFFICIENT INFORMATION": "verdict-insufficient",
            }

            if is_stream:
                first_line = ""
                rest_chunks = []
                for chunk in analysis_data:
                    first_line += chunk
                    if '\n' in first_line:
                        parts = first_line.split('\n', 1)
                        first_line = parts[0]
                        if parts[1]:
                            rest_chunks.append(parts[1])
                        break

                if first_line.startswith("Verdict:"):
                    verdict_value = first_line.replace("Verdict:", "").strip().upper()
                    css_class = verdict_class_map.get(verdict_value, "verdict-insufficient")
                    st.markdown(
                        templates.get("verdict-banner", css_class=css_class, verdict_value=verdict_value),
                        unsafe_allow_html=True
                    )
                    st.markdown(templates.get("analysis-label"), unsafe_allow_html=True)
                else:
                    st.markdown(templates.get("analysis-label"), unsafe_allow_html=True)
                    rest_chunks.insert(0, first_line + "\n")

                def stream_rest():
                    for c in rest_chunks:
                        yield c
                    for chunk in analysis_data:
                        yield chunk

                st.write_stream(stream_rest)
            else:
                analysis_text = analysis_data
                if analysis_text.startswith("Verdict:"):
                    lines = analysis_text.split('\n', 1)
                    verdict_value = lines[0].replace("Verdict:", "").strip().upper()
                    css_class = verdict_class_map.get(verdict_value, "verdict-insufficient")
                    st.markdown(
                        templates.get("verdict-banner", css_class=css_class, verdict_value=verdict_value),
                        unsafe_allow_html=True
                    )
                    st.markdown(templates.get("analysis-label"), unsafe_allow_html=True)
                    if len(lines) > 1:
                        st.markdown(lines[1].strip())
                else:
                    st.markdown(templates.get("analysis-label"), unsafe_allow_html=True)
                    st.markdown(analysis_text)

            # --- Sources ---
            if sources:
                st.markdown(templates.get("sources-header"), unsafe_allow_html=True)
                num_columns = 3
                cols = st.columns(num_columns)
                for i, source_url in enumerate(sources):
                    with cols[i % num_columns]:
                        st.markdown(f"[{source_url}]({source_url})")

    except Exception as e:
        status.markdown(templates.get("error-box", message=f"Error: {str(e)}"), unsafe_allow_html=True)
        progress.empty()

# --- Footer ---
st.markdown(templates.get("footer"), unsafe_allow_html=True)
