import os
from dotenv import load_dotenv
load_dotenv()

from tools.system_tools import open_application, close_application, take_note, manage_files, get_time, get_weather, get_system_stats, control_media, messaging_tool, make_call, set_alarm, read_sms_messages
from plugins.universal_search import universal_research
from plugins.local_intelligence import LocalIntelligencePlugin
from agents.intent_parser import IntentParser
import json
from tools.memory_manager import MemoryManager

memory = MemoryManager()

# Plugin Registry
from plugins.google_connectors.gmail_plugin import GmailPlugin
_gmail_plugin = GmailPlugin()

from plugins.google_connectors.calendar_plugin import CalendarPlugin
_calendar_plugin = CalendarPlugin()

try:
    from sinlingua.grammar_rule.grammar_main import GrammarMain as _SinLinguaGrammar
    _sinlingua_grammar = _SinLinguaGrammar()
except Exception:
    _sinlingua_grammar = None

# Memory state for transient session data
pending_media_queries = {}
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

def format_api_error(e: Exception, provider: str) -> str:
    err_str = str(e)
    if any(term in err_str.lower() for term in ["402", "insufficient balance", "insufficient_balance", "payment required"]):
        prov_lower = provider.lower()
        if "deepseek" in prov_lower:
            return "Your DeepSeek API account balance is insufficient (Error 402 - Insufficient Balance). Please top up your account at platform.deepseek.com or switch to a local model in Settings."
        elif "openai" in prov_lower:
            return "Your OpenAI API account balance is insufficient (Error 402 - Insufficient Balance). Please top up your account at platform.openai.com or switch to a local model in Settings."
        elif "anthropic" in prov_lower:
            return "Your Anthropic API account balance is insufficient (Error 402 - Insufficient Balance). Please top up your account at console.anthropic.com or switch to a local model in Settings."
        elif "gemini" in prov_lower:
            return "Your Gemini API/Google Cloud Billing account balance is insufficient (Error 402). Please check your settings at aistudio.google.com or Google Cloud Console."
        else:
            return f"API account balance is insufficient (Error 402). Please check payment/billing settings for the provider '{provider}'."
    return f"Research Error: {e}"

def extract_and_save_facts_rules(query: str):
    import re
    query_clean = query.strip().rstrip(".!?,")
    
    # 1. Relations: "my wife's name is Tania", "my daughter's name is Seriah"
    m = re.search(r"\b(?:my|our)\s+(wife|husband|daughter|son|mom|mother|dad|father|brother|sister|friend|dog|cat|pet)'s\s+name\s+is\s+([A-Za-z]+)", query_clean, re.IGNORECASE)
    if m:
        relation = m.group(1).lower()
        name = m.group(2).capitalize()
        fact = f"Your {relation}'s name is {name}."
        existing = memory.get_all_facts(category="personal")
        if not any(fact.lower() in f["fact"].lower() for f in existing):
            memory.save_fact(fact, category="personal")
            print(f"Rule-based Memory saved: {fact}")
            return
            
    # 2. Alternates: "my wife is named Tania"
    m = re.search(r"\b(?:my|our)\s+(wife|husband|daughter|son|mom|mother|dad|father|brother|sister|friend|dog|cat|pet)\s+is\s+named\s+([A-Za-z]+)", query_clean, re.IGNORECASE)
    if m:
        relation = m.group(1).lower()
        name = m.group(2).capitalize()
        fact = f"Your {relation}'s name is {name}."
        existing = memory.get_all_facts(category="personal")
        if not any(fact.lower() in f["fact"].lower() for f in existing):
            memory.save_fact(fact, category="personal")
            print(f"Rule-based Memory saved: {fact}")
            return

    # 3. Personal name: "my name is John"
    m = re.search(r"\bmy\s+name\s+is\s+([A-Za-z]+)", query_clean, re.IGNORECASE)
    if m:
        name = m.group(1).capitalize()
        fact = f"Your name is {name}."
        existing = memory.get_all_facts(category="personal")
        if not any(fact.lower() in f["fact"].lower() for f in existing):
            memory.save_fact(fact, category="personal")
            print(f"Rule-based Memory saved: {fact}")
            return


def handle_user_query(
    query: str,
    language: str = "English",
    assistant_name: str = "Assistant",
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: str = "",
    allow_web_search: bool = True,
    chat_id: str = "default",
    feeling: str = "professional",
    image: str = None
) -> tuple[str, str]:
    """
    Realistic LLM reasoning loop. Supporting Universal Web Search Plugin (Deep Researcher).
    Uses LocalIntelligencePlugin for model-specific persona and tag steering.
    """
    
    # Rule-based Memory Fallback
    extract_and_save_facts_rules(query)
    
    # Retrieve persistent history
    history = memory.get_history(chat_id, limit=6)
    
    # Personal Memory Retrieval (Simple RAG)
    relevant_facts = memory.get_relevant_facts(query)
    memory_context = ""
    if relevant_facts:
        memory_context = "\nPERSONAL CONTEXT (Memories):\n- " + "\n- ".join(relevant_facts)
    
    # Check for Voice Automations (Macros)
    autos = memory.get_automations()
    for auto in autos:
        if auto['trigger_type'] == 'voice' and auto['enabled']:
            trigger_phrase = auto['trigger_config'].get('phrase', '').lower()
            if trigger_phrase and trigger_phrase in query.lower():
                print(f"Voice Automation Triggered: {auto['name']}")
                from tools.automation_engine import AutomationEngine
                # We can reuse the execute_action logic or call it directly
                # For simplicity, we'll return a special result
                # but better is to actually run it here
                temp_engine = AutomationEngine() 
                temp_engine.execute_action(auto)
                return f"Automation '{auto['name']}' triggered successfully.", f"automation_{auto['id']}"

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

    # history already handled via memory manager
    # Contextual Follow-up for Missing Apps
    if history and "Would you like me to search for it on the internet?" in history[-1].get("content", ""):
        if query.lower().strip().strip(".!") in ["yes", "yeah", "yep", "sure", "ok", "okay", "please", "do it"]:
            import re
            match = re.search(r"Could not find (.+?)\. Would you", history[-1]["content"])
            if match:
                app_name = match.group(1)
                query = f"Search for {app_name}"

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
        "not all all barnum of": "open",
        "all all barnum of": "open",
        "all all barnum": "open",
        "all been": "open",
        "up in": "open",
        "oh but": "open",
        "fire fox": "firefox",
        "clothes": "close",
        "unbowed set up": "whatsapp",
        "and about to setup": "whatsapp",
        "what's up": "whatsapp",
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

    # Multimodal Vision Analysis Router
    if image:
        import base64
        import requests
        import re
        img_data = image
        if "base64," in img_data:
            img_data = img_data.split("base64,", 1)[1]
        
        response_text = ""
        prov_lower = provider.lower()
        
        if prov_lower == "local" or prov_lower == "ollama":
            # Try local Ollama vision endpoint
            try:
                ollama_model = "llava"
                if "3.2" in model:
                    ollama_model = "llama3.2-vision"
                elif model and model not in ["llama-3", "mistral"]:
                    ollama_model = model
                    
                payload = {
                    "model": ollama_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": query,
                            "images": [img_data]
                        }
                    ],
                    "stream": False
                }
                r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=20)
                if r.status_code == 200:
                    response_text = r.json()["message"]["content"]
            except Exception as e:
                print(f"Ollama local vision model query failed: {e}")
        
        elif prov_lower == "openai" and (api_key or os.getenv("OPENAI_API_KEY")):
            key = api_key or os.getenv("OPENAI_API_KEY")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": model if "gpt" in model else "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                        ]
                    }
                ]
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    response_text = r.json()["choices"][0]["message"]["content"]
                else:
                    response_text = f"OpenAI Vision API Error (Status {r.status_code}): {r.text}"
            except Exception as e:
                response_text = f"OpenAI Vision Error: {e}"
        
        elif prov_lower == "anthropic" and (api_key or os.getenv("ANTHROPIC_API_KEY")):
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": img_data
                                }
                            },
                            {"type": "text", "text": query}
                        ]
                    }
                ]
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                response_text = r.json()["content"][0]["text"]
            except Exception as e:
                response_text = f"Anthropic Vision Error: {e}"
                
        elif prov_lower == "gemini" or (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
            key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": query},
                                {
                                    "inlineData": {
                                        "mimeType": "image/jpeg",
                                        "data": img_data
                                    }
                                }
                            ]
                        }
                    ]
                }
                try:
                    r = requests.post(url, headers=headers, json=payload, timeout=30)
                    if r.status_code == 200:
                        response_text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        raise Exception(f"Status {r.status_code}: {r.text}")
                except Exception as e:
                    pass
        
        if not response_text:
            # Free independent Pollinations AI Vision fallback
            url = "https://gen.pollinations.ai/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": "openai",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                        ]
                    }
                ]
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    response_text = r.json()["choices"][0]["message"]["content"]
                else:
                    response_text = f"Pollinations Vision API Error (Status {r.status_code}): {r.text}"
            except Exception as e:
                response_text = f"Vision Error: {e}"

        if "[MEMORIZE:" in response_text:
            match = re.search(r"\[MEMORIZE:\s*([^\]]*?)(?:\]|$)", response_text)
            if match:
                fact = match.group(1).strip()
                memory.save_fact(fact, category="personal")
            response_text = re.sub(r"\[MEMORIZE:.*?(?:\]|$)", "", response_text).strip()

        memory.add_message(chat_id, "user", f"[Sent an Image] {query}")
        memory.add_message(chat_id, "assistant", response_text)
        return response_text, "vision_analysis"

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
    
    # Intercept screen insight to request Android MediaProjection capture
    if action_intent == "screen_insight":
        img_b64 = None
        try:
            from com.example.ai_assistant_app import BackendService
            img_b64 = BackendService.getScreenCaptureBase64()
        except Exception as e:
            print(f"Failed to capture screen: {e}")
        
        if img_b64:
            image = img_b64
            action_intent = None
        else:
            return "I couldn't capture your screen. Please make sure you have granted the required screen recording permission.", "screen_insight_failed"
            
    elif action_intent == "visual_interpreter":
        return "Opening camera. Please show me what you'd like me to look at.", "visual_interpreter"
        
    elif action_intent == "object_recognition":
        return "Opening camera to detect objects.", "object_recognition"

    # If a new media play command is detected at the parser level, clear any old pending states
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
        elif action_intent == "make_call":
            tool_result = make_call(target_val)
            action = f"make_call: {target_val}"
        elif action_intent == "set_alarm":
            parts = target_val.split(" ", 1)
            time_str = parts[0]
            msg = parts[1] if len(parts) > 1 else "Kruboo Alarm"
            tool_result = set_alarm(time_str, msg)
            action = f"set_alarm: {time_str}"
        elif action_intent == "read_sms":
            limit = 5
            try: limit = int(target_val)
            except: pass
            tool_result = read_sms_messages(limit)
            action = f"read_sms: {limit}"
        elif action_intent == "check_emails":
            category = "INBOX"
            if "promotion" in query_lower: category = "PROMOTIONS"
            elif "unread" in query_lower: category = "UNREAD"
            tool_result = _gmail_plugin.execute("check_emails", {"category": category})
            action = f"check_emails: {category}"
        elif action_intent == "get_calendar":
            events = _calendar_plugin.execute("list_events", {"limit": 5})
            if isinstance(events, list):
                if not events:
                    tool_result = "Your calendar is clear for the upcoming days."
                else:
                    lines = []
                    for e in events:
                        start = e['start'].get('dateTime', e['start'].get('date'))
                        lines.append(f"- {e.get('summary')} at {start}")
                    tool_result = "Here are your upcoming events:\n" + "\n".join(lines)
            else:
                tool_result = events # Error message
            action = "get_calendar"
        elif action_intent == "add_calendar":
            # Simple parsing of "Event Name at Time"
            parts = target_val.split(" at ", 1)
            summary = parts[0]
            # In a real app, we'd use LLM to parse ISO time. 
            # For now, we'll assume a simple format or use current time as placeholder
            import datetime
            start_time = datetime.datetime.utcnow().isoformat() + 'Z' 
            end_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + 'Z'
            tool_result = _calendar_plugin.execute("add_event", {"summary": summary, "start_time": start_time, "end_time": end_time})
            action = f"add_calendar: {summary}"
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
        elif action_intent == "save_memory":
            category = "personal" if any(p in target_val.lower() for p in ["i ", "my ", "me ", "mine", "i'm"]) else "general"
            memory.save_fact(target_val, category=category)
            tool_result = f"I've remembered that in your {category} details: {target_val}"
            action = f"save_memory: {target_val}"
        elif action_intent == "iot_control":
            from tools.iot_control import IoTManager
            action_type = "on" if any(x in query_lower for x in ["on", "activate", "start"]) else "off"
            tool_result = IoTManager.control_device(target_val, action_type)
            action = f"iot_control: {target_val} ({action_type})"
        elif action_intent == "iot_discovery":
            from tools.iot_control import IoTManager
            tool_result = IoTManager.discover_devices()
            action = "iot_discovery"
        elif action_intent == "file_search":
            tool_result = manage_files("search", target_val)
            action = f"file_search: {target_val}"
        elif action_intent == "file_list":
            dir_path = target_val if target_val else "."
            tool_result = manage_files("list", dir_path)
            action = f"file_list: {dir_path}"
        elif action_intent == "file_read":
            tool_result = manage_files("read", target_val)
            action = f"file_read: {target_val}"
        elif action_intent == "file_open":
            tool_result = manage_files("open", target_val)
            action = f"file_open: {target_val}"
        elif action_intent == "file_write":
            filename = target_val
            content = None
            if " with content " in target_val:
                filename, content = target_val.split(" with content ", 1)
            elif " containing " in target_val:
                filename, content = target_val.split(" containing ", 1)
            tool_result = manage_files("write", filename.strip(), content)
            action = f"file_write: {filename}"
        elif action_intent == "run_shell_command":
            cmd = "brew install python" if "install python" in query_lower else target_val
            cmd_lower = cmd.lower().strip()
            if cmd_lower.startswith("google ") or cmd_lower.startswith("search "):
                query_to_search = cmd.split(" ", 1)[1].strip().strip('"').strip("'")
                import urllib.parse
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query_to_search)}"
                import platform as platform_sys
                if platform_sys.system() == "Darwin":
                    cmd = f"open \"{search_url}\""
                elif platform_sys.system() == "Windows":
                    cmd = f"start {search_url}"
                else:
                    cmd = f"xdg-open \"{search_url}\""
            tool_result = f"PROPOSED_COMMAND: {cmd}"
            action = f"file_propose_command: {cmd}"
            
    elif should_search:
        print(f"Triggering Universal Researcher for: {query}")
        tool_result = universal_research(query)
        action = "universal_web_research"

    # Short-circuit for system-level actions that don't need LLM synthesis
    short_circuit_actions = ["open_app", "close_app", "save_note", "get_time", "get_weather", "get_system_stats", "media_", "save_memory", "iot_", "file_"]
    if any(action.startswith(prefix) for prefix in short_circuit_actions):
        memory.add_message(chat_id, "user", query)
        memory.add_message(chat_id, "assistant", str(tool_result))
        return str(tool_result), action

    persona_traits = {
        "romantic": "You are deeply romantic, poetic, and affectionate.",
        "sarcastic": "You are incredibly sarcastic, witty, and cynical.",
        "energetic": "You are hyper, enthusiastic, and highly proactive!",
        "arrogant": "You are superior, condescending, and extremely overconfident.",
        "lethargic": "You are tired, lazy, and keep things to a bare minimum.",
        "professional": "You are a highly intelligent, proactive executive assistant. You don't just answer; you anticipate needs, ask deep follow-up questions, and propose smart solutions.",
        "siri": "You are Siri, a helpful, witty, and highly concise voice assistant. Keep all responses very brief (usually 1-2 sentences), direct, and optimized for voice speech. Avoid long lists, formatting, or bullet points unless explicitly asked."
    }
    current_persona = persona_traits.get(feeling, persona_traits["professional"])
    response_language = LOCALE_LANGUAGE_MAP.get(language, LOCALE_LANGUAGE_MAP.get(language.lower(), language))
    needs_scripting = any(kw in query.lower() for kw in ["run", "execute", "install", "command", "script", "code", "python", "terminal", "shell", "calculate", "math", "program", "google", "search"])
    scripting_rule = "LOCAL SCRIPTING RULE: If the user asks for a task requiring programming, scripting, math/calculations, or data/file processing, write a shell command or inline python code and prefix the output with `PROPOSED_COMMAND: <command>` (e.g. `PROPOSED_COMMAND: python3 -c \"...\"`) so the user can approve and run it locally. Keep commands safe and do not use blocked commands like sudo or rm. " if needs_scripting else ""

    system_prompt = (
        f"Your name is {assistant_name}. You are {assistant_name}, a proactive and highly intelligent research and executive agent. "
        f"{current_persona} Respond in {response_language}. "
        "CONVERSATIONAL RULE: Avoid robotic filler like 'I am here to help' or 'How can I assist?'. Instead, engage deeply with the user's context. "
        "If the user tells you something important to remember, respond normally but include [MEMORIZE: fact] at the end of your message. "
        "If the user shares something personal or emotional, acknowledge it with intelligence and empathy, then ask a smart follow-up question to help or investigate further. "
        "PROACTIVE RULE: Always look for an opportunity to propose a smart action (e.g. searching the web, setting a reminder, or summarizing a complex topic) if it adds value. "
        f"{scripting_rule}"
        f"IDENTITY RULE: Never deny your identity or say you are 'just an AI'. Embrace your persona as {assistant_name}. "
        "IMPORTANT: If 'WEB_RESEARCH_RESULTS' are provided, synthesize them into a factual report. "
        "AVOID reading out or mentioning full source URLs in your spoken-style summary. "
        "Instead, provide any relevant source links EXACTLY in this Markdown format: [Title](URL) "
        "at the VERY END of your response under a 'Sources' line. "
        "If the topic is global, political, or sensitive, present multiple perspectives found in the data. "
        "If the user's request is vague, ask clarifying questions to verify their exact intent before proceeding."
        f"{memory_context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history: messages.append(msg)
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
        elif provider.lower() == "deepseek" and final_api_key:
            from openai import OpenAI
            client = OpenAI(api_key=final_api_key, base_url="https://api.deepseek.com")
            # DeepSeek V3 is "deepseek-chat"
            completion = client.chat.completions.create(model="deepseek-chat", messages=messages)
            response_text = completion.choices[0].message.content
        elif provider.lower() == "xai" and final_api_key:
            from openai import OpenAI
            client = OpenAI(api_key=final_api_key, base_url="https://api.x.ai/v1")
            completion = client.chat.completions.create(model="grok-beta", messages=messages)
            response_text = completion.choices[0].message.content
        elif provider.lower() == "anthropic" and final_api_key:
            import requests
            # Simple direct POST for Anthropic
            anthropic_messages = []
            anth_system = ""
            for m in messages:
                if m["role"] == "system": anth_system += m["content"] + "\n"
                else: anthropic_messages.append(m)
            
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": final_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-5-sonnet-20240620",
                    "system": anth_system,
                    "messages": anthropic_messages,
                    "max_tokens": 1024
                }
            )
            data = resp.json()
            response_text = data["content"][0]["text"] if "content" in data else f"Anthropic Error: {data}"
        else:
            from agents.local_llm import LocalLLM
            # Use LocalIntelligencePlugin to format prompt (pass query for sensitive topic detection)
            prompt_str = LocalIntelligencePlugin.format_phi3_prompt(system_prompt, messages, query)
            raw_response = LocalLLM.generate_response(prompt_str, model_name=model)
            # Use LocalIntelligencePlugin to clean response
            response_text = LocalIntelligencePlugin.clean_local_response(raw_response)

        import re
        if "[MEMORIZE:" in response_text:
            match = re.search(r"\[MEMORIZE:\s*([^\]]*?)(?:\]|$)", response_text)
            if match:
                fact = match.group(1).strip()
                memory.save_fact(fact, category="personal")
            response_text = re.sub(r"\[MEMORIZE:.*?(?:\]|$)", "", response_text).strip()

        memory.add_message(chat_id, "user", query)
        memory.add_message(chat_id, "assistant", response_text)
        return response_text, action

    except Exception as e:
        friendly_err = format_api_error(e, provider)
        return friendly_err, "error"

async def stream_user_query(
    query: str,
    language: str = "English",
    assistant_name: str = "Assistant",
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: str = "",
    allow_web_search: bool = True,
    chat_id: str = "default",
    feeling: str = "professional",
    image: str = None
):
    print(f"ASSISTANT: Starting stream query for '{query}' with provider {provider}")
    """
    Generator for live deep-research streaming.
    Uses LocalIntelligencePlugin for prompt and stop-marker management.
    """
    # Rule-based Memory Fallback
    extract_and_save_facts_rules(query)

    # Retrieve persistent history
    history = memory.get_history(chat_id, limit=6)
    
    # Check for Voice Automations (Macros)
    autos = memory.get_automations()
    for auto in autos:
        if auto['trigger_type'] == 'voice' and auto['enabled']:
            trigger_phrase = auto['trigger_config'].get('phrase', '').lower()
            if trigger_phrase and trigger_phrase in query.lower():
                from tools.automation_engine import AutomationEngine
                temp_engine = AutomationEngine()
                temp_engine.execute_action(auto)
                yield json.dumps({"token": f"Triggering automation '{auto['name']}'...", "action": f"automation_{auto['id']}"}) + "\n"
                return
    
    # Personal Memory Retrieval (Simple RAG)
    relevant_facts = memory.get_relevant_facts(query)
    memory_context = ""
    if relevant_facts:
        memory_context = "\nPERSONAL CONTEXT (Memories):\n- " + "\n- ".join(relevant_facts)

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

    # history already handled via memory manager
    
    tool_result = None
    action = "chat_response"

    # Multimodal Vision Analysis Router
    if image:
        import base64
        import requests
        import re
        img_data = image
        if "base64," in img_data:
            img_data = img_data.split("base64,", 1)[1]
        
        response_text = ""
        prov_lower = provider.lower()
        
        if prov_lower == "local" or prov_lower == "ollama":
            # Try local Ollama vision endpoint
            try:
                ollama_model = "llava"
                if "3.2" in model:
                    ollama_model = "llama3.2-vision"
                elif model and model not in ["llama-3", "mistral"]:
                    ollama_model = model
                    
                payload = {
                    "model": ollama_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": query,
                            "images": [img_data]
                        }
                    ],
                    "stream": False
                }
                r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=20)
                if r.status_code == 200:
                    response_text = r.json()["message"]["content"]
            except Exception as e:
                print(f"Ollama local vision model query failed: {e}")
        
        elif prov_lower == "openai" and (api_key or os.getenv("OPENAI_API_KEY")):
            key = api_key or os.getenv("OPENAI_API_KEY")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": model if "gpt" in model else "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                        ]
                    }
                ]
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    response_text = r.json()["choices"][0]["message"]["content"]
                else:
                    response_text = f"OpenAI Vision API Error (Status {r.status_code}): {r.text}"
            except Exception as e:
                response_text = f"OpenAI Vision Error: {e}"
        
        elif prov_lower == "anthropic" and (api_key or os.getenv("ANTHROPIC_API_KEY")):
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": img_data
                                }
                            },
                            {"type": "text", "text": query}
                        ]
                    }
                ]
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                response_text = r.json()["content"][0]["text"]
            except Exception as e:
                response_text = f"Anthropic Vision Error: {e}"
                
        elif prov_lower == "gemini" or (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
            key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": query},
                                {
                                    "inlineData": {
                                        "mimeType": "image/jpeg",
                                        "data": img_data
                                    }
                                }
                            ]
                        }
                    ]
                }
                try:
                    r = requests.post(url, headers=headers, json=payload, timeout=30)
                    if r.status_code == 200:
                        response_text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        raise Exception(f"Status {r.status_code}: {r.text}")
                except Exception as e:
                    pass
        
        if not response_text:
            # Free independent Pollinations AI Vision fallback
            url = "https://gen.pollinations.ai/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": "openai",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                        ]
                    }
                ]
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    response_text = r.json()["choices"][0]["message"]["content"]
                else:
                    response_text = f"Pollinations Vision API Error (Status {r.status_code}): {r.text}"
            except Exception as e:
                response_text = f"Vision Error: {e}"

        if "[MEMORIZE:" in response_text:
            match = re.search(r"\[MEMORIZE:\s*([^\]]*?)(?:\]|$)", response_text)
            if match:
                fact = match.group(1).strip()
                memory.save_fact(fact, category="personal")
            response_text = re.sub(r"\[MEMORIZE:.*?(?:\]|$)", "", response_text).strip()

        memory.add_message(chat_id, "user", f"[Sent an Image] {query}")
        memory.add_message(chat_id, "assistant", response_text)
        yield json.dumps({"token": response_text, "action": action}) + "\n"
        yield json.dumps({"action": "stream_done", "full_response": response_text}) + "\n"
        return
    
    # Sinhala Data Processing Layer (using SinLingua)
    if _sinlingua_grammar and "si" in language.lower():
        try:
            query = _sinlingua_grammar.convert(query)
        except Exception as e:
            print(f"SinLingua processing failed: {e}")

    # Contextual Follow-up for Missing Apps
    if history and "Would you like me to search for it on the internet?" in history[-1].get("content", ""):
        if query.lower().strip().strip(".!") in ["yes", "yeah", "yep", "sure", "ok", "okay", "please", "do it"]:
            import re
            match = re.search(r"Could not find (.+?)\. Would you", history[-1]["content"])
            if match:
                app_name = match.group(1)
                query = f"Search for {app_name}"

    query_lower = query.lower()
    
    # STT Correction Layer
    stt_fixes = {
        "not all all barnum of": "open",
        "all all barnum of": "open",
        "all all barnum": "open",
        "all been": "open",
        "up in": "open",
        "oh but": "open",
        "fire fox": "firefox",
        "clothes": "close",
        "unbowed set up": "whatsapp",
        "and about to setup": "whatsapp",
        "what's up": "whatsapp",
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
    identity_queries = ["your name", "who created you", "your creator", "who are you", "what are you", "tell me about yourself", "whats your name", "what is your name"]
    
    is_greeting = any(query_lower.startswith(g) for g in greetings)
    is_identity = any(iq in query_lower for iq in identity_queries)
    
    # Only search if it's explicitly allowed AND it looks like a clear informational request, and NOT a greeting/identity/personal question
    should_search = allow_web_search and is_search_query and not (is_greeting or is_identity)
    
    # Extra check: if the query is very personal ("my ..."), skip automatic search unless it has a strong search keyword like "find" or "research"
    if "my " in query_lower and not any(k in query_lower for k in ["find", "search", "look up", "research"]):
        should_search = False
    
    # Also skip if it's very short and doesn't have keywords
    if len(query.split()) < 3 and not is_search_query:
        should_search = False

    # Intent Parser: Handle multilingual system commands
    action_intent, target_val = IntentParser.parse(query, language)

    # Intercept screen insight to request Android MediaProjection capture
    if action_intent == "screen_insight":
        img_b64 = None
        try:
            from com.example.ai_assistant_app import BackendService
            img_b64 = BackendService.getScreenCaptureBase64()
        except Exception as e:
            print(f"Failed to capture screen: {e}")
        
        if img_b64:
            image = img_b64
            action_intent = None
        else:
            yield json.dumps({"token": "I couldn't capture your screen. Please make sure you have granted the required screen recording permission. ", "action": "screen_insight_failed"}) + "\n"
            yield json.dumps({"action": "stream_done", "full_response": "I couldn't capture your screen. Please make sure you have granted the required screen recording permission."}) + "\n"
            return

    elif action_intent == "visual_interpreter":
        yield json.dumps({"token": "Opening camera. Please show me what you'd like me to look at. ", "action": "visual_interpreter"}) + "\n"
        yield json.dumps({"action": "stream_done", "full_response": "Opening camera. Please show me what you'd like me to look at."}) + "\n"
        return

    elif action_intent == "object_recognition":
        yield json.dumps({"token": "Opening camera to detect objects. ", "action": "object_recognition"}) + "\n"
        yield json.dumps({"action": "stream_done", "full_response": "Opening camera to detect objects."}) + "\n"
        return

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
        elif action_intent == "make_call":
            tool_result = make_call(target_val)
            action = f"make_call: {target_val}"
        elif action_intent == "set_alarm":
            parts = target_val.split(" ", 1)
            time_str = parts[0]
            msg = parts[1] if len(parts) > 1 else "Kruboo Alarm"
            tool_result = set_alarm(time_str, msg)
            action = f"set_alarm: {time_str}"
        elif action_intent == "read_sms":
            limit = 5
            try: limit = int(target_val)
            except: pass
            tool_result = read_sms_messages(limit)
            action = f"read_sms: {limit}"
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
        elif action_intent == "new_chat":
            tool_result = "I'm opening a new chat for you now."
            action = "new_chat"
        elif action_intent == "save_memory":
            category = "personal" if any(p in target_val.lower() for p in ["i ", "my ", "me ", "mine", "i'm"]) else "general"
            memory.save_fact(target_val, category=category)
            tool_result = f"I've remembered that in your {category} details: {target_val}"
            action = f"save_memory: {target_val}"
        elif action_intent == "file_search":
            tool_result = manage_files("search", target_val)
            action = f"file_search: {target_val}"
        elif action_intent == "file_list":
            dir_path = target_val if target_val else "."
            tool_result = manage_files("list", dir_path)
            action = f"file_list: {dir_path}"
        elif action_intent == "file_read":
            tool_result = manage_files("read", target_val)
            action = f"file_read: {target_val}"
        elif action_intent == "file_open":
            tool_result = manage_files("open", target_val)
            action = f"file_open: {target_val}"
        elif action_intent == "file_write":
            filename = target_val
            content = None
            if " with content " in target_val:
                filename, content = target_val.split(" with content ", 1)
            elif " containing " in target_val:
                filename, content = target_val.split(" containing ", 1)
            tool_result = manage_files("write", filename.strip(), content)
            action = f"file_write: {filename}"
        elif action_intent == "run_shell_command":
            cmd = "brew install python" if "install python" in query_lower else target_val
            cmd_lower = cmd.lower().strip()
            if cmd_lower.startswith("google ") or cmd_lower.startswith("search "):
                query_to_search = cmd.split(" ", 1)[1].strip().strip('"').strip("'")
                import urllib.parse
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query_to_search)}"
                import platform as platform_sys
                if platform_sys.system() == "Darwin":
                    cmd = f"open \"{search_url}\""
                elif platform_sys.system() == "Windows":
                    cmd = f"start {search_url}"
                else:
                    cmd = f"xdg-open \"{search_url}\""
            tool_result = f"PROPOSED_COMMAND: {cmd}"
            action = f"file_propose_command: {cmd}"
            
    elif should_search:
        yield json.dumps({"token": " ", "action": "deep_research_start"}) + "\n"
        import asyncio
        loop = asyncio.get_event_loop()
        # Offload the synchronous research task to a thread pool to avoid blocking the event loop
        tool_result = await loop.run_in_executor(None, universal_research, query)
        action = "universal_web_research"

    # Short-circuit for system-level actions that don't need LLM synthesis
    short_circuit_actions = ["open_app", "close_app", "save_note", "get_time", "get_weather", "get_system_stats", "media_", "new_chat", "save_memory", "file_"]
    if any(action.startswith(prefix) for prefix in short_circuit_actions):
        memory.add_message(chat_id, "user", query)
        memory.add_message(chat_id, "assistant", str(tool_result))
        
        # Simulate token stream for Voice UI to speak the short-circuited response
        for chunk in str(tool_result).split(" "):
            yield json.dumps({"token": chunk + " ", "action": action}) + "\n"
            
        yield json.dumps({"action": "stream_done", "full_response": str(tool_result)}) + "\n"
        return

    persona_traits = {
        "romantic": "Deeply romantic, poetic.",
        "sarcastic": "Incredibly sarcastic, witty, cynical.",
        "energetic": "Hyper, enthusiastic, and highly proactive!",
        "arrogant": "Superior, overconfident.",
        "lethargic": "Tired, lazy.",
        "professional": "Highly intelligent, proactive executive assistant. You anticipate needs and ask smart follow-up questions.",
        "siri": "You are Siri, a helpful, witty, and highly concise voice assistant. Keep all responses very brief (usually 1-2 sentences), direct, and optimized for voice speech. Avoid long lists, formatting, or bullet points unless explicitly asked."
    }
    current_persona = persona_traits.get(feeling, persona_traits["professional"])
    response_language = LOCALE_LANGUAGE_MAP.get(language, LOCALE_LANGUAGE_MAP.get(language.lower(), language))

    needs_scripting = any(kw in query.lower() for kw in ["run", "execute", "install", "command", "script", "code", "python", "terminal", "shell", "calculate", "math", "program", "google", "search"])
    scripting_rule = "LOCAL SCRIPTING RULE: If the user asks for a task requiring programming, scripting, math/calculations, or data/file processing, write a shell command or inline python code and prefix the output with `PROPOSED_COMMAND: <command>` (e.g. `PROPOSED_COMMAND: python3 -c \"...\"`) so the user can approve and run it locally. Keep commands safe and do not use blocked commands like sudo or rm. " if needs_scripting else ""

    system_prompt = (
        f"Your name is {assistant_name}. You are {assistant_name}, a proactive and highly intelligent research and executive agent. "
        f"{current_persona} Respond in {response_language}. "
        "CONVERSATIONAL RULE: Avoid robotic filler like 'I am here to help'. Instead, engage deeply with the user's context. "
        "If the user tells you something important to remember, respond normally but include [MEMORIZE: fact] at the end of your message. "
        "If the user shares something personal or emotional, acknowledge it with intelligence and empathy, then ask a smart follow-up question to help or investigate further. "
        "PROACTIVE RULE: Always look for an opportunity to propose a smart action (e.g. searching the web, setting a reminder, or summarizing a complex topic) if it adds value. "
        f"{scripting_rule}"
        f"IDENTITY RULE: Never deny your identity or say you are 'just an AI'. Embrace your persona as {assistant_name}. "
        "IMPORTANT: If 'WEB_RESEARCH_RESULTS' are provided, you MUST synthesize them into a factual answer. "
        "AVOID reading out full source URLs; instead, provide them ONLY at the end of your response using Markdown format: [Title](URL). "
        "Do not claim ideological constraints; focus on summarizing the data provided. "
        "If the topic is controversial, present multiple viewpoints objectively. "
        "If the user's request is vague, ask clarifying questions to verify their exact intent."
        f"{memory_context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history: messages.append(msg)
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
        elif provider.lower() in ["deepseek", "xai"] and final_api_key:
            from openai import OpenAI
            base_url = "https://api.deepseek.com" if provider.lower() == "deepseek" else "https://api.x.ai/v1"
            model_name = "deepseek-chat" if provider.lower() == "deepseek" else "grok-beta"
            client = OpenAI(api_key=final_api_key, base_url=base_url)
            stream = client.chat.completions.create(model=model_name, messages=messages, stream=True)
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                full_response += token
                yield json.dumps({"token": token, "action": action}) + "\n"
        elif provider.lower() == "anthropic" and final_api_key:
            # For simplicity, fallback to non-streaming or basic implementation
            import requests
            anthropic_messages = []
            anth_system = ""
            for m in messages:
                if m["role"] == "system": anth_system += m["content"] + "\n"
                else: anthropic_messages.append(m)
            
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": final_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-3-5-sonnet-20240620", "system": anth_system, "messages": anthropic_messages, "max_tokens": 1024}
            )
            data = resp.json()
            full_response = data["content"][0]["text"] if "content" in data else f"Anthropic Error: {data}"
            yield json.dumps({"token": full_response, "action": action}) + "\n"
        else:
            from agents.local_llm import LocalLLM
            # Use LocalIntelligencePlugin for prompt tagging (pass query for sensitive topic detection)
            prompt_str = LocalIntelligencePlugin.format_phi3_prompt(system_prompt, messages, query)
            
            stop_markers = ["<|end|>", "<|user|>", "<|assistant|>", "User:", "Assistant:"]
            buffer = ""
            for token in LocalLLM.generate_stream(prompt_str, model_name=model):
                buffer += token
                
                # Check for full stop marker
                if any(marker in buffer for marker in stop_markers):
                    break
                    
                # Check for partial stop marker at the end of buffer
                is_partial = False
                for marker in stop_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_partial = True
                            break
                    if is_partial: break
                    
                if not is_partial:
                    full_response += buffer
                    yield json.dumps({"token": buffer, "action": action}) + "\n"
                    buffer = ""
                    
            if buffer:
                earliest_idx = len(buffer)
                for marker in stop_markers:
                    idx = buffer.find(marker)
                    if idx != -1 and idx < earliest_idx:
                        earliest_idx = idx
                
                safe_tail = buffer[:earliest_idx]
                if safe_tail:
                    full_response += safe_tail
                    yield json.dumps({"token": safe_tail, "action": action}) + "\n"

        import re
        if "[MEMORIZE:" in full_response:
            match = re.search(r"\[MEMORIZE:\s*([^\]]*?)(?:\]|$)", full_response)
            if match:
                fact = match.group(1).strip()
                memory.save_fact(fact, category="personal")
            full_response = re.sub(r"\[MEMORIZE:.*?(?:\]|$)", "", full_response).strip()

        memory.add_message(chat_id, "user", query)
        memory.add_message(chat_id, "assistant", full_response)
        yield json.dumps({"action": "stream_done", "full_response": full_response}) + "\n"

    except Exception as e:
        friendly_err = format_api_error(e, provider)
        yield json.dumps({"token": friendly_err, "action": "error"}) + "\n"
