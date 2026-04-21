import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class ApiService {
  final String baseUrl = 'http://127.0.0.1:8000';
  final Dio _dio = Dio();

  Future<String?> transcribeAudio(File audioFile, String language, String? apiKey) async {
    try {
      FormData formData = FormData.fromMap({
        "file": await MultipartFile.fromFile(audioFile.path, filename: "voice.wav"),
        "language": language,
        if (apiKey != null && apiKey.isNotEmpty) "api_key": apiKey,
      });

      Response response = await _dio.post(
        "$baseUrl/transcribe",
        data: formData,
      );

      if (response.statusCode == 200) {
        return response.data['text'];
      }
    } catch (e) {
      debugPrint("Transcription error: $e");
    }
    return null;
  }

  Future<Map<String, dynamic>?> sendQuery({
    required String query,
    required bool isVoice,
    required String language,
    required String assistantName,
    required String llmProvider,
    required String llmModel,
    String? apiKey,
    bool allowWebSearch = true,
  }) async {
    try {
      Response response = await _dio.post(
        "$baseUrl/query",
        data: {
          'query': query,
          'is_voice': isVoice,
          'language': language,
          'assistant_name': assistantName,
          'llm_provider': llmProvider,
          'llm_model': llmModel,
          'api_key': apiKey ?? "",
          'allow_web_search': allowWebSearch,
        },
      );

      if (response.statusCode == 200) {
        return response.data;
      }
    } catch (e) {
      debugPrint("Query error: $e");
    }
    return null;
  }

  Future<File?> getTtsAudio(String text, String language) async {
    try {
      Response response = await _dio.post(
        "$baseUrl/tts",
        data: {"text": text, "language": language},
        options: Options(responseType: ResponseType.bytes),
      );

      if (response.statusCode == 200) {
        // Save to temp file
        final tempDir = Directory.systemTemp;
        final file = File('${tempDir.path}/tts_output.mp3');
        await file.writeAsBytes(response.data);
        return file;
      }
    } catch (e) {
      debugPrint("TTS error: $e");
    }
    return null;
  }
}
