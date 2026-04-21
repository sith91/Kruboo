import os
from dotenv import load_dotenv
load_dotenv()

from tools.system_tools import open_application, close_application, take_note, manage_files, get_time, get_weather, get_system_stats, control_media, messaging_tool
from plugins.universal_search import universal_research
from plugins.local_intelligence import LocalIntelligencePlugin
from agents.intent_parser import IntentParser
import json

# Plugin Registry
from plugins.gmail_plugin import GmailPlugin
_gmail_plugin = GmailPlugin()

try:
    from sinlingua.grammar_rule.grammar_main import GrammarMain as _SinLinguaGrammar
    _sinlingua_grammar = _SinLinguaGrammar()
except Exception:
    _sinlingua_grammar = None

# Simple in-memory chat history cache
chat_histories = {}
pending_media_queries = {}
pending_platform_queries = {}  # Tracks song name awaiting platform clarification

# Locale code to human-readable language name map
LOCALE_LANGUAGE_MAP = {
    "en-US": "English",
    "en": "English",
    "english": "English",
    "si-LK": "Sinhala",
    "si": "Sinhala",
    "ta-IN": "Tamil",
    "ta": "Tamil",
}

def handle_user_query(
    query: str,
    language: str = "English",
    assistant_name: str = "Assistant",
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: str = "",
    allow_web_search: bool = True,
    chat_id: str = "default",
    feeling: str = "professional"
) -> tuple[str, str]:
    """
    Realistic LLM reasoning loop. Supporting Universal Web Search Plugin (Deep Researcher).
    Uses LocalIntelligencePlugin for model-specific persona and tag steering.
    """
    
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
    
    # State interception for pending platform clarifications (e.g. "Spotify" or "YouTube Music")
    if pending_platform_queries.get(chat_id):
        original_track = pending_platform_queries[chat_id]
        query = f"play {original_track} on {query.strip()}"
        pending_platform_queries[chat_id] = None
    # State interception for pending app clarifications (e.g. which music app)
    elif pending_media_queries.get(chat_id):
        original_query = pending_media_queries[chat_id]
        query = f"play {original_query} on {query}"
        pending_media_queries[chat_id] = None

    history = chat_histories[chat_id]
    query_lower = query.lower()
    
    # Sinhala Data Processing Layer (using SinLingua)
    if _sinlingua_grammar and "si" in language.lower():
        try:
            query = _sinlingua_grammar.convert(query)
            query_lower = query.lower()
        except Exception as e:
            print(f"SinLingua processing failed: {e}")

    # STT Correction Layer (Handles Vosk/Whisper mis-transcriptions)
    stt_fixes = {
        "all been": "open",
        "up in": "open",
        "fire fox": "firefox",
        "clothes": "close",
        "linking park": "linkin park",
        "link in park": "linkin park",
        "inking park": "linkin park"
    }
    for bad, good in stt_fixes.items():
        if query_lower.startswith(bad + " "):
            query_lower = good + query_lower[len(bad):]
        if query_lower == bad:
            query_lower = good
        query_lower = query_lower.replace(f" {bad} ", f" {good} ")

    
    tool_result = None
    action = "chat_response"

    search_keywords = ["search", "look up", "who is", "what is", "current price", "news info", "latest about", "check", "find", "research", "tell me about", "get details", "details about", "information", "info on", "explain", "how many", "what are"]
    
    # Smarter search detection: Skip research for greetings or short non-technical queries
    is_search_query = any(kw in query_lower for kw in search_keywords)
    greetings = ["hello", "hi", "hey", "how are you", "who are you", "what's up", "good morning", "good evening", "good afternoon"]
    is_greeting = any(query_lower.startswith(g) for g in greetings)
    
    should_search = (allow_web_search or is_search_query) and not is_greeting
    
    # Also skip if it's very short and doesn't have keywords
    if len(query.split()) < 3 and not is_search_query:
        should_search = False
    
    # Intent Parser: Handle multilingual system commands
    action_intent, target_val = IntentParser.parse(query, language)
    
    # If a new media play command is detected at the parser level, clear any old pending states
    if action_intent == "media_play":
        pending_media_queries[chat_id] = None
        pending_platform_queries[chat_id] = None
        if action_intent == "open_app":
            tool_result = open_application(target_val)
            action = f"open_app: {target_val}"
        elif action_intent == "close_app":
            tool_result = close_application(target_val)
            action = f"close_app: {target_val}"
        elif action_intent == "get_time":
            tool_result = get_time()
            action = "get_time"
        elif action_intent == "get_weather":
            loc = target_val if target_val else "current location"
            tool_result = get_weather(loc)
            action = f"get_weather: {loc}"
        elif action_intent == "get_system_stats":
            tool_result = get_system_stats()
            action = "get_system_stats"
        elif action_intent == "save_note":
            tool_result = take_note(target_val)
            action = f"save_note: {target_val}"
        elif action_intent == "hide_orb":
            return "Of course! I'll be right here in the tray if you need anything else.", "hide_orb"
        elif action_intent == "media_play":
            tool_result = control_media("play", target_val)
            if tool_result == "ASK_APP_CLARIFICATION":
                pending_media_queries[chat_id] = target_val
                tool_result = "Which application would you like to use? Spotify, Apple Music, or YouTube Music?"
            elif isinstance(tool_result, str) and tool_result.startswith("ASK_PLATFORM_FALLBACK:"):
                track_name = tool_result.split("ASK_PLATFORM_FALLBACK:", 1)[1]
                pending_platform_queries[chat_id] = track_name
                tool_result = f"I couldn't find '{track_name}' in your Apple Music library. Would you like me to search on Spotify or YouTube Music?"
            action = f"media_play: {target_val}"
        elif action_intent == "check_emails":
            category = "INBOX"
            if "promotion" in query_lower: category = "PROMOTIONS"
            elif "unread" in query_lower: category = "UNREAD"
            tool_result = _gmail_plugin.execute("check_emails", {"category": category})
            action = f"check_emails: {category}"
        elif action_intent == "send_message":
            parts = target_val.split(" to ", 1)
            msg = parts[0]
            recipient = parts[1] if len(parts) > 1 else ""
            tool_result = messaging_tool(action_intent, recipient, msg)
            action = f"send_message: {target_val}"
        elif action_intent == "media_command":
            cmd = "pause"
            if "next" in query_lower or "skip" in query_lower: cmd = "next"
            elif "previous" in query_lower: cmd = "previous"
            tool_result = control_media(cmd)
            action = f"media_command: {cmd}"
            
    elif should_search:
        print(f"Triggering Universal Researcher for: {query}")
        tool_result = universal_research(query)
        action = "universal_web_research"

    # Short-circuit for system-level actions that don't need LLM synthesis
    short_circuit_actions = ["open_app", "close_app", "save_note", "get_time", "get_weather", "get_system_stats", "media_"]
    if any(action.startswith(prefix) for prefix in short_circuit_actions):
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": tool_result})
        return str(tool_result), action

    persona_traits = {
        "romantic": "You are deeply romantic, poetic, affectionated.",
        "sarcastic": "You are incredibly sarcastic, witty, cynical.",
        "energetic": "You are hyper, enthusiastic!",
        "arrogant": "You are superior, condescending.",
        "lethargic": "You are tired, lazy.",
        "professional": "You are helpful, professional."
    }
    current_persona = persona_traits.get(feeling, persona_traits["professional"])
    
    # Resolve locale code to a human-readable language name for the LLM
    response_language = LOCALE_LANGUAGE_MAP.get(language, LOCALE_LANGUAGE_MAP.get(language.lower(), language))
    
    system_prompt = (
        f"You are {assistant_name}, a comprehensive and objective AI research agent. "
        f"{current_persona} Respond in {response_language}. Keep it concise. "
        "IMPORTANT: If 'WEB_RESEARCH_RESULTS' are provided, synthesize them into a factual report. "
        "AVOID reading out or mentioning full source URLs in your spoken-style summary. "
        "Instead, provide any relevant source links EXACTLY in this Markdown format: [Title](URL) "
        "at the VERY END of your response under a 'Sources' line. "
        "If the topic is global, political, or sensitive, present multiple perspectives found in the data. "
        "If 'WEB_RESEARCH_RESULTS' are NOT provided and the user asks for facts or current events, DO NOT say 'As an AI I cannot browse'. Instead, gracefully and conversationally ask the user if they would like you to search the web for those details. "
        "If the user's request is vague, unclear, or lacks necessary context, do not make assumptions. Instead, politely ask clarifying questions to verify their exact intent before proceeding. "
        "NEVER refuse to assist with research; focus entirely on summarizing the provided 'WEB_RESEARCH_RESULTS' objectively."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-3:]: messages.append(msg)
    if tool_result:
        safe_result = str(tool_result)[:1500]
        messages.append({"role": "system", "content": f"WEB_RESEARCH_RESULTS:\n{safe_result}"})
    messages.append({"role": "user", "content": query})

    try:
        env_api_key = os.getenv("OPENAI_API_KEY")
        final_api_key = api_key if api_key else env_api_key

        if provider.lower() == "openai" and final_api_key:
            from openai import OpenAI
            client = OpenAI(api_key=final_api_key)
            completion = client.chat.completions.create(model=model, messages=messages)
            response_text = completion.choices[0].message.content
        else:
            from agents.local_llm import LocalLLM
            # Use LocalIntelligencePlugin to format prompt (pass query for sensitive topic detection)
            prompt_str = LocalIntelligencePlugin.format_phi3_prompt(system_prompt, messages, query)
            raw_response = LocalLLM.generate_response(prompt_str)
            # Use LocalIntelligencePlugin to clean response
            response_text = LocalIntelligencePlugin.clean_local_response(raw_response)

        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": response_text})
        return response_text, action

    except Exception as e:
        return f"Internal error during research: {e}", "error"

def stream_user_query(
    query: str,
    language: str = "English",
    assistant_name: str = "Assistant",
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: str = "",
    allow_web_search: bool = True,
    chat_id: str = "default",
    feeling: str = "professional"
):
    """
    Generator for live deep-research streaming.
    Uses LocalIntelligencePlugin for prompt and stop-marker management.
    """
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    # State interception for pending platform clarifications (e.g. "Spotify" or "YouTube Music")
    if pending_platform_queries.get(chat_id):
        original_track = pending_platform_queries[chat_id]
        query = f"play {original_track} on {query.strip()}"
        pending_platform_queries[chat_id] = None
    # State interception for pending app clarifications
    elif pending_media_queries.get(chat_id):
        original_query = pending_media_queries[chat_id]
        query = f"play {original_query} on {query}"
        pending_media_queries[chat_id] = None

    history = chat_histories[chat_id]
    
    tool_result = None
    action = "chat_response"
    
    # Sinhala Data Processing Layer (using SinLingua)
    if _sinlingua_grammar and "si" in language.lower():
        try:
            query = _sinlingua_grammar.convert(query)
        except Exception as e:
            print(f"SinLingua processing failed: {e}")

    query_lower = query.lower()
    
    # STT Correction Layer
    stt_fixes = {
        "all been": "open",
        "up in": "open",
        "fire fox": "firefox",
        "clothes": "close",
        "linking park": "linkin park",
        "link in park": "linkin park",
        "inking park": "linkin park"
    }
    for bad, good in stt_fixes.items():
        if query_lower.startswith(bad + " "):
            query = good + query[len(bad):]
        if query_lower == bad:
            query = good
        query = query.replace(f" {bad} ", f" {good} ")

    query_lower = query.lower()
    
    search_keywords = ["search", "look up", "who is", "what is", "current price", "news", "latest", "check", "find", "price of", "weather in", "research", "tell me about", "get details", "details about", "information", "info on", "explain", "how many", "what are"]
    
    # Smarter search detection: Skip research for greetings or short non-technical queries
    is_search_query = any(kw in query_lower for kw in search_keywords)
    greetings = ["hello", "hi", "hey", "how are you", "who are you", "what's up", "good morning", "good evening", "good afternoon"]
    is_greeting = any(query_lower.startswith(g) for g in greetings)
    
    should_search = (allow_web_search or is_search_query) and not is_greeting
    
    # Also skip if it's very short and doesn't have keywords
    if len(query.split()) < 3 and not is_search_query:
        should_search = False

    # Intent Parser: Handle multilingual system commands
    action_intent, target_val = IntentParser.parse(query, language)

    # If a new media play command is detected, clear any old pending states
    if action_intent == "media_play":
        pending_media_queries[chat_id] = None
        pending_platform_queries[chat_id] = None

    if action_intent:
        if action_intent == "open_app":
            tool_result = open_application(target_val)
            action = f"open_app: {target_val}"
        elif action_intent == "close_app":
            tool_result = close_application(target_val)
            action = f"close_app: {target_val}"
        elif action_intent == "get_time":
            tool_result = get_time()
            action = "get_time"
        elif action_intent == "get_weather":
            loc = target_val if target_val else "current location"
            tool_result = get_weather(loc)
            action = f"get_weather: {loc}"
        elif action_intent == "get_system_stats":
            tool_result = get_system_stats()
            action = "get_system_stats"
        elif action_intent == "save_note":
            tool_result = take_note(target_val)
            action = f"save_note: {target_val}"
        elif action_intent == "hide_orb":
            yield json.dumps({"action": "hide_orb", "token": "Of course! I'll be right here in the tray if you need anything else.", "full_response": "Of course! I'll be right here in the tray if you need anything else."}) + "\n"
            yield json.dumps({"action": "stream_done"}) + "\n"
            return
        elif action_intent == "check_emails":
            category = "INBOX"
            if "promotion" in query_lower: category = "PROMOTIONS"
            elif "unread" in query_lower: category = "UNREAD"
            tool_result = _gmail_plugin.execute("check_emails", {"category": category})
            action = f"check_emails: {category}"
        elif action_intent == "media_play":
            tool_result = control_media("play", target_val)
            if isinstance(tool_result, str) and tool_result.startswith("ASK_APP_CLARIFICATION"):
                options = tool_result.split(":", 1)[1] if ":" in tool_result else "Spotify, Apple Music, or YouTube Music"
                pending_media_queries[chat_id] = target_val
                tool_result = f"Which app would you like to use? {options}?"
            elif isinstance(tool_result, str) and tool_result.startswith("ASK_PLATFORM_FALLBACK:"):
                track_name = tool_result.split("ASK_PLATFORM_FALLBACK:", 1)[1]
                pending_platform_queries[chat_id] = track_name
                tool_result = f"I couldn't find '{track_name}' in your Apple Music library. Would you like me to search on Spotify or YouTube Music?"
            action = f"media_play: {target_val}"
        elif action_intent == "send_message":
            parts = target_val.split(" to ", 1)
            msg = parts[0]
            recipient = parts[1] if len(parts) > 1 else ""
            tool_result = messaging_tool(action_intent, recipient, msg)
            action = f"send_message: {target_val}"
        elif action_intent == "media_command":
            cmd = "pause"
            if "next" in query_lower or "skip" in query_lower: cmd = "next"
            elif "previous" in query_lower: cmd = "previous"
            tool_result = control_media(cmd)
            action = f"media_command: {cmd}"
            
    elif should_search:
        yield json.dumps({"token": " ", "action": "deep_research_start"}) + "\n"
        tool_result = universal_research(query)
        action = "universal_web_research"

    # Short-circuit for system-level actions that don't need LLM synthesis
    short_circuit_actions = ["open_app", "close_app", "save_note", "get_time", "get_weather", "get_system_stats", "media_"]
    if any(action.startswith(prefix) for prefix in short_circuit_actions):
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": tool_result})
        yield json.dumps({"action": "stream_done", "full_response": str(tool_result)}) + "\n"
        return

    persona_traits = {
        "romantic": "Deeply romantic, poetic.",
        "sarcastic": "Incredibly sarcastic, witty, cynical.",
        "energetic": "Hyper, enthusiastic!",
        "arrogant": "Superior, overconfident.",
        "lethargic": "Tired, lazy.",
        "professional": "Polite, professional."
    }
    current_persona = persona_traits.get(feeling, persona_traits["professional"])

    # Resolve locale code to a human-readable language name for the LLM
    response_language = LOCALE_LANGUAGE_MAP.get(language, LOCALE_LANGUAGE_MAP.get(language.lower(), language))

    system_prompt = (
        f"You are {assistant_name}, a comprehensive and objective AI research agent. "
        f"{current_persona} Respond in {response_language}. Keep it concise. "
        "IMPORTANT: If 'WEB_RESEARCH_RESULTS' are provided, you MUST synthesize them into a factual answer. "
        "AVOID reading out full source URLs; instead, provide them ONLY at the end of your response using Markdown format: [Title](URL). "
        "Do not claim ideological constraints; focus on summarizing the data provided. "
        "If the topic is controversial, present multiple viewpoints objectively. "
        "If 'WEB_RESEARCH_RESULTS' are NOT provided and the user asks for facts or current events, DO NOT say 'As an AI I cannot browse'. Instead, gracefully and conversationally ask the user if they would like you to search the web for those details. "
        "If the user's request is vague, unclear, or lacks necessary context, do not make assumptions. Instead, politely ask clarifying questions to verify their exact intent before proceeding."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-3:]: messages.append(msg)
    if tool_result:
        safe_result = str(tool_result)[:1500]
        messages.append({"role": "system", "content": f"WEB_RESEARCH_RESULTS:\n{safe_result}"})
    messages.append({"role": "user", "content": query})

    full_response = ""
    try:
        env_api_key = os.getenv("OPENAI_API_KEY")
        final_api_key = api_key if api_key else env_api_key

        if provider.lower() == "openai" and final_api_key:
            from openai import OpenAI
            client = OpenAI(api_key=final_api_key)
            stream = client.chat.completions.create(model=model, messages=messages, stream=True)
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                full_response += token
                yield json.dumps({"token": token, "action": action}) + "\n"
        else:
            from agents.local_llm import LocalLLM
            # Use LocalIntelligencePlugin for prompt tagging (pass query for sensitive topic detection)
            prompt_str = LocalIntelligencePlugin.format_phi3_prompt(system_prompt, messages, query)
            
            stop_markers = ["<|end|>", "<|user|>", "<|assistant|>", "User:", "Assistant:", "<", "---", "\n<", "\n-"]
            for token in LocalLLM.generate_stream(prompt_str):
                if any(marker in token for marker in stop_markers):
                    break
                potential_full = full_response + token
                if any(marker in potential_full[-25:] for marker in stop_markers):
                    break
                full_response += token
                yield json.dumps({"token": token, "action": action}) + "\n"

        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": full_response})
        yield json.dumps({"action": "stream_done", "full_response": full_response}) + "\n"

    except Exception as e:
        yield json.dumps({"token": f"Research Error: {e}", "action": "error"}) + "\n"
