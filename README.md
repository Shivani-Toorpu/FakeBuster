# FakeBuster

**Multilingual LLM-Based System for Real-Time Automated Verification of News Claims**

FakeBuster validates news headlines using Llama models via Groq, and the Tavily Search API. It uses native tool calling to search for relevant real-time news sources and analyzes their content to determine the veracity of a given headline. It supports multilingual claims in English, Hindi, Telugu, and Tamil.

## Features

-   **News Headline Validation**: Checks claims and outputs a verdict (TRUE, FALSE, PARTIALLY TRUE, INSUFFICIENT INFORMATION).
-   **Integration with Groq**: Uses Llama models for incredibly fast inference and analysis.
-   **Native Tool Calling**: Dynamically calls the Tavily Search API to pull up-to-date sources.
-   **Multilingual Support**: Detects input language (English, Hindi, Telugu, Tamil) and responds in the same language.
-   **Chain-of-Thought Reasoning**: Uses structured internal reasoning for higher accuracy verdicts.
-   **Dynamic Search Depth**: Choose between "Quick Search" and "Deep Dive" modes.
-   **Real-time Streaming**: Streams the AI's analysis directly to the UI.
-   **Streamlit Interface**: Clean, newspaper-inspired minimalist frontend.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:** (Optional but recommended)
    ```bash
    python -m venv my_env
    # On Windows
    .\my_env\Scripts\activate
    # On macOS/Linux
    source my_env/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Create a `.env` file in the root directory and add your API keys:
    ```env
    GROQ_API_KEY="YOUR_GROQ_API_KEY"
    TAVILY_API_KEY="YOUR_TAVILY_API_KEY"
    ```

## Usage

Run the Streamlit application:

```bash
streamlit run news_validator.py
```

Open your web browser and navigate to the local URL provided by Streamlit (usually `http://localhost:8501`). Enter a news headline in the input field, configure your Search Depth, and click "Verify This Claim" to start the analysis.
