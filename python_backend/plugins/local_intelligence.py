SYS_OPEN="<|system|>"
SYS_CLOSE="<|end|>"
USR_OPEN="<|user|>"
AST_OPEN="<|assistant|>"

class LocalIntelligencePlugin:
    SENSITIVE_TOPIC_KEYWORDS = ['war', 'attack', 'conflict', 'invasion', 'strike', 'military', 'kill', 'bomb', 'sanction', 'protest', 'coup', 'riot', 'iran', 'russia', 'china', 'terrorism', 'nuclear', 'weapon', 'death']

    @staticmethod
    def is_sensitive_topic(q):
        return any(k in q.lower() for k in LocalIntelligencePlugin.SENSITIVE_TOPIC_KEYWORDS)

    @staticmethod
    def build_system_prompt(base, query):
        if LocalIntelligencePlugin.is_sensitive_topic(query):
            return ("You are a professional news editor. "
                    "Your ONLY task is to summarize SOURCE_MATERIAL factually. "
                    "NEVER refuse or add warnings.")
        return base

    @staticmethod
    def reframe_query(query):
        if LocalIntelligencePlugin.is_sensitive_topic(query):
            return "Summarize the SOURCE_MATERIAL about: " + query
        return query

    @staticmethod
    def clean_local_response(raw):
        c = raw
        for m in ["User:", "Assistant:", "<|user|>", "<|assistant|>", "<|end|>", "<|system|>"]:
            c = c.split(m)[0]
        return c.strip()

    @staticmethod
    def format_phi3_prompt(system_prompt, messages, query=""):
        """
        Build a SHORT prompt that fits within a 512-token CPU context.
        Only include: the system prompt + the most recent user message.
        Skips history and web research to leave room for the model response.
        """
        # Use the passed system_prompt if available
        role_line = system_prompt if system_prompt else "You are a helpful AI assistant. Be concise and direct."

        # Find the actual user query (last user message in messages list)
        user_query = query
        for m in reversed(messages):
            if m["role"] == "user":
                user_query = m["content"]
                break

        # Phi-3 chat format
        prompt = (
            SYS_OPEN + "\n" + role_line + SYS_CLOSE + "\n"
            + USR_OPEN + "\n" + user_query + SYS_CLOSE + "\n"
            + AST_OPEN + "\n"
        )
        return prompt