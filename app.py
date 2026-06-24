from langdetect import detect
import os
import re
import json
from tavily import TavilyClient
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Debug: Check if keys are loaded
print(f"TAVILY_API_KEY loaded: {'Yes' if TAVILY_API_KEY else 'No'}")
print(f"GROQ_API_KEY loaded: {'Yes' if GROQ_API_KEY else 'No'}")

# Initialize clients
try:
    print("Initializing Tavily client...")
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
    print("Initializing Groq client...")
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except Exception as e:
    print(f"Error initializing clients: {e}")

# System prompt template
SYSTEM_PROMPT_TEMPLATE = """You are a professional fact-checker specializing in verifying news claims. Your job is to determine if a claim is true, false, partially true, or insufficient information, based on real information found on the web.

For each claim:
1. First, call the search_web tool to find relevant information.
2. Analyze all the information thoroughly and consider the credibility of sources.
3. Provide a clear verdict: TRUE, FALSE, PARTIALLY TRUE, or INSUFFICIENT INFORMATION.

Your goal is to help users distinguish between real and fake news with evidence-based analysis.

Always remember your thumb rule: No matter the query is repeated or it has been asked by the user in the past, you should always use the search tool to search. 
Even if you know the answer already, you must perform a web search first.

ONLY after receiving the search results, you may generate your final verdict.

Do not add years until mentioned by the user in the input.

OUTPUT LANGUAGE RULE:
- The word "Verdict:" must always be written in English (it is a machine-parseable token).
- The verdict value (TRUE / FALSE / PARTIALLY TRUE / INSUFFICIENT INFORMATION) must always be in English.
- The entire analysis paragraph MUST be written strictly in {target_language}.
- Do not write the analysis in English unless {target_language} is English.

OUTPUT FORMAT (you MUST follow this exactly):
Line 1: Verdict: [ONE OF: TRUE, FALSE, PARTIALLY TRUE, INSUFFICIENT INFORMATION]
Line 2: (blank line)
Line 3+: [Your analysis paragraph in {target_language}]

Never combine the verdict line and the analysis on the same line. They must be separated by a newline."""

def search_web(query, time_range="month", search_depth="basic", max_results=5):
    """
    Search the web for information using Tavily API
    """
    topic = "general"
    
    print(f"Performing Tavily search for '{query}' with time_range='{time_range}'")
    print(f" -> Using settings: topic='{topic}', depth='{search_depth}', max_results={max_results}")
    
    valid_time_ranges = ["day", "week", "month", "year", "none"]
    if time_range not in valid_time_ranges:
        print(f"Invalid time_range '{time_range}', defaulting to 'month'")
        time_range = "month"
        
    try:
        # Perform the search with Tavily
        response = tavily_client.search(
            query=query,
            topic=topic,
            search_depth=search_depth,
            max_results=max_results,
            time_range=time_range if time_range != "none" else None,
            include_answer="advanced"
        )
        return response
    except Exception as e:
        print(f"Error searching with Tavily: {e}")
        return {"error": f"Error searching with Tavily: {str(e)}"}

def execute_function_call(function_call, default_time_range, default_search_depth, default_max_results):
    name = function_call.function.name
    try:
        parameters = json.loads(function_call.function.arguments)
    except Exception as e:
        parameters = {}
    
    print(f"Executing function: {name} with parameters: {parameters}")
    
    if name == 'search_web':
        query = parameters.get('query', '')
        time_range = parameters.get('time_range', default_time_range)
        
        result = search_web(query, time_range, search_depth=default_search_depth, max_results=default_max_results)
        
        if isinstance(result, dict) and 'error' in result:
            print(f"Error during search_web execution: {result['error']}")
            return f"Error: {result['error']}"
            
        if isinstance(result, dict):
            formatted_results = "Search Results:\n\n"
            if result.get('answer'):
                formatted_results += f"Summary: {result.get('answer')}\n\n"
            
            formatted_results += "Sources:\n"
            sources_list = []
            for i, search_result in enumerate(result.get('results', []), 1):
                url = search_result.get('url', 'No URL')
                title = search_result.get('title', 'No Title')
                content = search_result.get('content', 'No content available')
                
                formatted_results += f"{i}. {title}\n"
                formatted_results += f"   URL: {url}\n"
                formatted_results += f"   Content: {content[:200]}...\n\n"
                
                if url and url != "No URL":
                    sources_list.append(url)
            
            return {
                "formatted_text": formatted_results,
                "sources": sources_list
            }
        return str(result)
    else:
        return f"Error: Function {name} is not implemented"

def process_user_input(user_input, time_range="month", search_depth="basic", max_results=5, status_callback=None):
    if not tavily_client or not groq_client:
        return {"response": "API Keys for Groq and Tavily must be configured.", "sources": [], "is_stream": False}

    effective_time_range = time_range if time_range in ["none", "day", "week", "month", "year"] else "month"
    print(f"\n----- PROCESSING INPUT: '{user_input}' with time_range: '{effective_time_range}', depth: '{search_depth}' -----")
    
    def update_status(message, progress=None):
        print(f"STATUS: {message} (Progress: {progress}%)")
        if status_callback:
            status_callback(message, progress)
            
    try:
        # Language Detection
        try:
            detected_lang_code = detect(user_input)
            lang_map = {'en': 'ENGLISH', 'hi': 'HINDI', 'te': 'TELUGU', 'ta': 'TAMIL'}
            target_language = lang_map.get(detected_lang_code, 'the same language as the input')
            print(f"Detected language code: {detected_lang_code}, Target: {target_language}")
        except Exception as e:
            print(f"Language detection failed: {e}")
            target_language = 'the same language as the input'
            
        update_status("Sending query to Llama-4...", 25)
        
        time_range_prompt = f"Please use the time range '{effective_time_range}' for your search."
        if effective_time_range == 'none':
            time_range_prompt = "Please perform the search without any specific time range limitation."
            
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(target_language=target_language)
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_input}\n\n{time_range_prompt}"}
        ]
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for information related to a news headline or claim",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query related to the news or claim to verify"
                            },
                            "time_range": {
                                "type": "string",
                                "enum": ["none", "day", "week", "month", "year"],
                                "description": "Time range to limit search results."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        print("Sending request to Groq API for tool call...")
        completion = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            tools=tools,
            tool_choice="required",
            temperature=0.7,
            max_completion_tokens=1024
        )
        
        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls
        
        if not tool_calls:
            update_status("No search needed, generating direct response...", 90)
            return {"response": response_message.content, "sources": [], "is_stream": False}
        
        update_status(f"Searching for information within time range: '{effective_time_range}'...", 50)
        messages.append(response_message)
        
        all_sources = []
        for tool_call in tool_calls:
            update_status(f"Executing {tool_call.function.name}...", 60)
            result = execute_function_call(tool_call, effective_time_range, search_depth, max_results)
            
            if isinstance(result, dict) and 'formatted_text' in result:
                tool_response = result['formatted_text']
                if 'sources' in result:
                    all_sources.extend(result['sources'])
            else:
                tool_response = result
                
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_call.function.name,
                "content": str(tool_response),
            })
            
        messages.append({
            "role": "user", 
            "content": f"Based on these search results, determine whether the original claim is true or fake.\n\n"
                       f"You MUST follow these steps in order:\n\n"
                       f"STEP 1 — SCRATCHPAD (mandatory):\n"
                       f"Wrap your internal reasoning in <scratchpad> and </scratchpad> tags.\n"
                       f"Inside the scratchpad, do ALL of the following in English:\n"
                       f"  a) Restate the original claim.\n"
                       f"  b) For EACH search result, note whether it supports, contradicts, or is irrelevant to the claim.\n"
                       f"  c) Evaluate source credibility (official govt/org sites > news agencies > blogs/social media).\n"
                       f"  d) Identify any conflicting information between sources.\n"
                       f"  e) State your conclusion and why.\n\n"
                       f"STEP 2 — FINAL OUTPUT (after </scratchpad>):\n"
                       f"Output EXACTLY this format with a blank line between the verdict and analysis:\n\n"
                       f"Verdict: [ONE OF: TRUE, FALSE, PARTIALLY TRUE, INSUFFICIENT INFORMATION]\n\n"
                       f"[Your one-paragraph analysis in {target_language}]\n\n"
                       f"RULES:\n"
                       f"- The word 'Verdict:' and the verdict value (TRUE/FALSE/etc.) must be in English.\n"
                       f"- The analysis paragraph must be in {target_language}.\n"
                       f"- Do NOT include any URLs or source links.\n"
                       f"- Do NOT put the verdict and analysis on the same line."
        })
        
        update_status("Generating final analysis...", 85)
        print("Sending final request to Groq API with streaming...")
        final_completion = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            temperature=0.7,
            max_completion_tokens=1024,
            stream=True
        )
        
        update_status("Finalizing response...", 95)
        unique_sources = list(dict.fromkeys(all_sources)) 
        
        def generate_response():
            in_scratchpad = False
            buffer = ""
            for chunk in final_completion:
                content = chunk.choices[0].delta.content
                if not content:
                    continue
                buffer += content
                
                while True:
                    if not in_scratchpad:
                        if "<scratchpad>" in buffer:
                            parts = buffer.split("<scratchpad>", 1)
                            if parts[0]:
                                yield parts[0]
                            buffer = parts[1]
                            in_scratchpad = True
                        else:
                            # Safe to yield if no partial match at the end
                            partial_match = False
                            for i in range(1, len("<scratchpad>")):
                                if buffer.endswith("<scratchpad>"[:i]):
                                    partial_match = True
                                    # Yield everything before the partial match
                                    safe_len = len(buffer) - i
                                    if safe_len > 0:
                                        yield buffer[:safe_len]
                                        buffer = buffer[safe_len:]
                                    break
                            
                            if not partial_match:
                                yield buffer
                                buffer = ""
                            break # Wait for next chunk
                    else:
                        if "</scratchpad>" in buffer:
                            parts = buffer.split("</scratchpad>", 1)
                            buffer = parts[1]
                            in_scratchpad = False
                        else:
                            if len(buffer) > 15:
                                buffer = buffer[-15:]
                            break # Wait for next chunk
                            
            if not in_scratchpad and buffer:
                buffer = buffer.strip()
                if buffer:
                    yield buffer
                    
        update_status("Complete!", 100)
        return {
            "response": generate_response(),
            "sources": unique_sources,
            "is_stream": True
        }
        
    except Exception as e:
        print(f"ERROR in process_user_input: {e}")
        import traceback
        traceback.print_exc()
        return {"response": f"An error occurred during processing: {str(e)}", "sources": [], "is_stream": False}

if __name__ == "__main__":
    user_input = "Is it true that PM Modi announced 15 lakhs to every Indian citizen?"
    result = process_user_input(user_input)
    if result.get("is_stream"):
        for chunk in result["response"]:
            print(chunk, end="")
    else:
        print(result.get("response"))