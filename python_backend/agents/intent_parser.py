import json
import os

class IntentParser:
    _intents = {}

    @classmethod
    def load_intents(cls, language: str):
        # Cache the intents so we don't read disk on every query
        if language in cls._intents:
            return cls._intents[language]

        # Use full module path
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Default to English if language string is malformed
        lang_code = "en"
        if "si" in language.lower():
            lang_code = "si"
            
        file_path = os.path.join(base_dir, "locales", f"intents_{lang_code}.json")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                intents = json.load(f)
                cls._intents[language] = intents
                return intents
        except Exception as e:
            print(f"Failed to load intent file: {file_path}. Error: {e}")
            # Fallback to empty mappings
            return {}

    @classmethod
    def parse(cls, query: str, language: str = "en-US") -> tuple[str, str]:
        """
        Parses a query and returns a tuple of (action_name, target_value)
        Returns (None, None) if no matching system intent is found.
        """
        query_lower = query.lower()
        
        # STT Correction Layer (Handles Vosk mis-transcriptions for common English commands)
        stt_fixes = {
            "all been": "open",
            "up in": "open",
            "fire fox": "firefox",
            "clothes": "close",
            "kruboo": "kruubu",
            "kru bu": "kruubu"
        }
        for bad, good in stt_fixes.items():
            query_lower = query_lower.replace(bad, good)
            
        # Wake word removal
        wake_word = "kruubu"
        if query_lower.startswith(wake_word + " "):
            query_lower = query_lower[len(wake_word):].strip()
        elif query_lower.startswith(wake_word):
            query_lower = query_lower[len(wake_word):].strip()
            
        intents = cls.load_intents(language)
        
        # ── New: Direct URL/Domain Recognition ──
        # If the query looks like a domain name, auto-trigger open_app
        url_pattern = r'^([a-zA-Z0-9-]+\.)+(com|net|org|io|gov|lk|me|dev|ai|app)(\/[^\s]*)?$'
        import re
        if re.match(url_pattern, query_lower):
            return "open_app", query_lower

        for action, trigger_phrases in intents.items():
            for phrase in trigger_phrases:
                if phrase in query_lower:
                    # Logic for extracting target value based on where the phrase is
                    if query_lower.startswith(phrase):
                        target = query_lower.replace(phrase, "", 1).strip()
                    else:
                        # If the phrase is in the middle, assume the target follows the phrase
                        target = query_lower.split(phrase, 1)[1].strip()
                    
                    # For specific intents that don't always need a target, return action
                    if action in ["hide_orb", "get_time"] and not target:
                        return action, ""
                    if action == "get_weather" and (not target or target == "today"):
                        target = "current location"
                        
                    return action, target
                    
        return None, None
