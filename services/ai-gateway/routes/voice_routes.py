# services/ai-gateway/routes/voice_routes.py
from fastapi import APIRouter, HTTPException
import logging
import asyncio

from models.base_models import VoiceCommandRequest, VoiceCommandResponse
from core.intent_analyzer import IntentAnalyzer
from core.workflow_engine import WorkflowEngine
from utils.config import load_config

router = APIRouter(tags=["voice"])

# Global instances
intent_analyzer = None
workflow_engine = None

async def initialize():
    global intent_analyzer, workflow_engine
    config = load_config()
    
    # Initialize intent analyzer
    intent_analyzer = IntentAnalyzer()
    await intent_analyzer.initialize()
    
    # Initialize workflow engine for voice-triggered workflows
    from core.model_selector import ModelSelector
    from providers.model_registry import ModelRegistry
    
    model_registry = ModelRegistry(config)
    await model_registry.initialize_providers()
    model_selector = ModelSelector(model_registry.get_providers())
    
    workflow_engine = WorkflowEngine(model_selector)
    await workflow_engine.initialize()

async def cleanup():
    if intent_analyzer:
        await intent_analyzer.cleanup()
    if workflow_engine:
        await workflow_engine.cleanup()

@router.post("/voice/command", response_model=VoiceCommandResponse)
async def process_voice_command(request: VoiceCommandRequest):
    """
    Complete voice command processing pipeline with workflow support
    """
    try:
        # 1. Speech to Text
        transcript = await _transcribe_audio(request.audio_data, request.language)

        # 2. Intent Analysis with workflow detection
        intent_result = await intent_analyzer.analyze(transcript.text)
        
        # 3. Check for workflow patterns
        if await _is_workflow_voice_command(transcript.text):
            workflow_intent = await _process_workflow_voice_command(transcript.text)
            if workflow_intent:
                # Merge workflow intent with original analysis
                intent_result = _merge_intents(intent_result, workflow_intent)

        # 4. Return structured command
        return VoiceCommandResponse(
            transcript=transcript.text,
            intent=intent_result.intent,
            confidence=intent_result.confidence * transcript.confidence,  # Combined confidence
            entities=intent_result.entities,
            action=intent_result.action,
            parameters=intent_result.parameters
        )

    except Exception as e:
        logging.error(f"Voice command processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/transcribe")
async def transcribe_audio(request: VoiceCommandRequest):
    """Pure speech-to-text transcription"""
    try:
        result = await _transcribe_audio(request.audio_data, request.language)
        return {
            "text": result.text,
            "confidence": result.confidence,
            "language": result.language,
            "is_final": result.is_final
        }
    except Exception as e:
        logging.error(f"Audio transcription failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/synthesize")
async def synthesize_speech(text: str, voice: str = "default"):
    """Text-to-speech synthesis"""
    try:
        audio_data = await _synthesize_speech(text, voice)
        return {
            "audio_data": audio_data,  # base64
            "format": "wav",
            "sample_rate": 24000,
            "voice": voice,
            "text_length": len(text)
        }
    except Exception as e:
        logging.error(f"Speech synthesis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/stream")
async def stream_voice_command(request: VoiceCommandRequest):
    """
    Stream processing for real-time voice commands
    Returns partial results as they become available
    """
    try:
        # This would integrate with streaming STT
        async def generate_transcriptions():
            # Simulate streaming transcription
            words = ["Processing", "voice", "command", "..."]
            for word in words:
                yield {
                    "type": "partial",
                    "text": word,
                    "is_final": False
                }
                await asyncio.sleep(0.1)
            
            final_transcript = await _transcribe_audio(request.audio_data, request.language)
            yield {
                "type": "final",
                "text": final_transcript.text,
                "is_final": True,
                "confidence": final_transcript.confidence
            }

        return generate_transcriptions()
        
    except Exception as e:
        logging.error(f"Voice streaming failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice/voices")
async def get_available_voices():
    """Get available TTS voices"""
    try:
        voices = await _get_available_voices()
        return {
            "voices": voices,
            "default_voice": "default"
        }
    except Exception as e:
        logging.error(f"Failed to get available voices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _is_workflow_voice_command(transcript: str) -> bool:
    """Detect workflow commands in voice transcripts"""
    workflow_phrases = [
        'create workflow', 'make automation', 'schedule task',
        'automate this', 'work setup', 'daily routine',
        'build workflow', 'create command', 'set up automation'
    ]
    transcript_lower = transcript.lower()
    return any(phrase in transcript_lower for phrase in workflow_phrases)

async def _process_workflow_voice_command(transcript: str):
    """Process workflow commands from voice"""
    try:
        if workflow_engine:
            # Use workflow engine to analyze the voice command
            workflow_analysis = await workflow_engine.analyze_voice_command(transcript)
            
            return {
                "intent": "create_workflow",
                "confidence": workflow_analysis.get('confidence', 0.8),
                "entities": workflow_analysis.get('entities', {}),
                "action": "create_workflow",
                "parameters": {
                    "transcript": transcript,
                    "workflow_type": workflow_analysis.get('workflow_type', 'automation'),
                    "suggested_steps": workflow_analysis.get('suggested_steps', [])
                }
            }
    except Exception as e:
        logging.warning(f"Workflow voice command processing failed: {e}")
    
    return None

def _merge_intents(original_intent, workflow_intent):
    """Merge original intent with workflow intent"""
    if not workflow_intent:
        return original_intent
    
    # Prefer workflow intent for workflow-related commands
    if workflow_intent.get('confidence', 0) > original_intent.confidence:
        # Create a merged intent object
        class MergedIntent:
            def __init__(self, original, workflow):
                self.intent = workflow.get('intent', original.intent)
                self.confidence = max(workflow.get('confidence', 0), original.confidence)
                self.entities = {**original.entities, **workflow.get('entities', {})}
                self.action = workflow.get('action', original.action)
                self.parameters = {**original.parameters, **workflow.get('parameters', {})}
        
        return MergedIntent(original_intent, workflow_intent)
    
    return original_intent

async def _transcribe_audio(audio_data: str, language: str):
    """Transcribe audio to text - integrates with your STT engine"""
    try:
        # This would integrate with your actual STT engine
        # For now, return a mock response
        return type('TranscriptionResult', (), {
            "text": "mock transcription from audio",
            "confidence": 0.9,
            "language": language,
            "is_final": True
        })()
    except Exception as e:
        logging.error(f"Audio transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

async def _synthesize_speech(text: str, voice: str) -> str:
    """Synthesize speech from text - integrates with your TTS engine"""
    try:
        # This would integrate with your actual TTS engine
        # Return base64 encoded audio
        return "base64_encoded_audio_data"
    except Exception as e:
        logging.error(f"Speech synthesis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

async def _get_available_voices():
    """Get available TTS voices"""
    # This would integrate with your TTS engine
    return [
        {"id": "default", "name": "Default Voice", "language": "en-US"},
        {"id": "female_1", "name": "Female Voice 1", "language": "en-US"},
        {"id": "male_1", "name": "Male Voice 1", "language": "en-US"}
    ]

# Health check endpoint for voice services
@router.get("/voice/health")
async def voice_health_check():
    """Health check for voice processing services"""
    services_status = {
        "intent_analyzer": intent_analyzer is not None,
        "workflow_engine": workflow_engine is not None,
        "stt_engine": True,  # Would check actual STT connection
        "tts_engine": True   # Would check actual TTS connection
    }
    
    all_healthy = all(services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": asyncio.get_event_loop().time(),
        "services": services_status
    }
