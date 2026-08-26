import 'dart:async';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_recognition_error.dart';

/// Service that continuously listens for a wake‑word (default: "Kruuboo").
/// It uses the [speech_to_text] plugin with partial results enabled.
/// When the wake‑word is detected it adds `null` to the [_wakeWordController]
/// stream which can be listened to from anywhere in the app.
class VoiceTriggerService {
  // Singleton pattern
  VoiceTriggerService._internal();
  static final VoiceTriggerService _instance = VoiceTriggerService._internal();
  factory VoiceTriggerService() => _instance;

  final stt.SpeechToText _speech = stt.SpeechToText();
  final StreamController<void> _wakeWordController = StreamController<void>.broadcast();
  Stream<void> get onWakeWordDetected => _wakeWordController.stream;

  bool _listening = false;
  final String wakeWord = "Kruuboo"; // can be made configurable later

  /// Initialise the SpeechToText engine. Call once, e.g. in `main()`.
  Future<void> init() async {
    final available = await _speech.initialize(
      onStatus: _statusListener,
      onError: _errorListener,
    );
    if (!available) {
      // SpeechToText not available – silently ignore.
      return;
    }
    await startListening();
  }

  Future<void> startListening() async {
    if (_listening) return;
    _listening = true;
    await _speech.listen(
      onResult: _resultListener,
      listenMode: stt.ListenMode.confirmation, // reduces system beeps
      partialResults: true,
      cancelOnError: true,
    );
  }

  Future<void> stopListening() async {
    if (!_listening) return;
    await _speech.stop();
    _listening = false;
  }

  void _resultListener(SpeechRecognitionResult result) {
    final words = result.recognizedWords.toLowerCase();
    if (words.contains(wakeWord.toLowerCase())) {
      // Wake‑word detected – emit an event.
      _wakeWordController.add(null);
      // Pause briefly to avoid immediate retriggers.
      stopListening();
      Future.delayed(const Duration(seconds: 2), () => startListening());
    }
  }

  void _statusListener(String status) {
    if (status == 'notListening' && _listening) {
      startListening();
    }
  }

  void _errorListener(SpeechRecognitionError error) {
    // Re‑initialize after a short delay on error.
    Future.delayed(const Duration(seconds: 1), () => init());
  }

  void dispose() {
    _wakeWordController.close();
    _speech.stop();
  }
}
