import re
from typing import Dict, Any, List
from dataclasses import dataclass
import logging

@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: Dict[str, Any]
    action: str
    parameters: Dict[str, Any]

class IntentAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.patterns = self._initialize_patterns()

    async def initialize(self):
        """Initialize the intent analyzer"""
        self.logger.info("Intent analyzer initialized")

    async def analyze(self, text: str) -> IntentResult:
        """Analyze text to extract intent and entities"""
        text_lower = text.lower().strip()
        
        # Check each pattern
        for intent_config in self.patterns:
            for pattern in intent_config['patterns']:
                match = re.search(pattern, text_lower)
                if match:
                    entities = intent_config['entity_extractor'](match, text)
                    return IntentResult(
                        intent=intent_config['intent'],
                        confidence=0.9,  # High confidence for pattern matches
                        entities=entities,
                        action=intent_config['action'],
                        parameters=intent_config.get('parameter_extractor', lambda m, t: {})(match, text)
                    )
        
        # Fallback to general intent
        return self._fallback_analysis(text)

    def _initialize_patterns(self) -> List[Dict]:
        """Initialize intent recognition patterns"""
        return [
            {
                'intent': 'open_application',
                'action': 'open_app',
                'patterns': [
                    r'open (.+)',
                    r'launch (.+)',
                    r'start (.+)',
                    r'run (.+)'
                ],
                'entity_extractor': self._extract_app_name,
                'parameter_extractor': self._extract_app_parameters
            },
            {
                'intent': 'search_web',
                'action': 'web_search',
                'patterns': [
                    r'search for (.+)',
                    r'find (.+)',
                    r'look up (.+)',
                    r'google (.+)'
                ],
                'entity_extractor': self._extract_search_query
            },
            {
                'intent': 'system_info',
                'action': 'get_system_info',
                'patterns': [
                    r'system info',
                    r'what\'s running',
                    r'show processes',
                    r'computer info'
                ],
                'entity_extractor': lambda m, t: {}
            },
            # Add more patterns as needed
        ]

    def _extract_app_name(self, match, text: str) -> Dict[str, Any]:
        return {'app_name': match.group(1).strip()}

    def _extract_app_parameters(self, match, text: str) -> Dict[str, Any]:
        return {'app_name': match.group(1).strip()}

    def _extract_search_query(self, match, text: str) -> Dict[str, Any]:
        return {'query': match.group(1).strip()}

    def _fallback_analysis(self, text: str) -> IntentResult:
        """Fallback analysis when no patterns match"""
        return IntentResult(
            intent='general_query',
            confidence=0.3,
            entities={'text': text},
            action='ai_process',
            parameters={'prompt': text}
        )
