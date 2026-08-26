import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

class ApiService {
  String _baseUrl = 'http://127.0.0.1:8000';
  String get baseUrl => _baseUrl;
  String? _syncToken;
  final Dio _dio = Dio();

  ApiService() {
    _loadSyncData();
  }

  Future<void> _loadSyncData() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString('api_base_url') ?? 'http://127.0.0.1:8000';
    _syncToken = prefs.getString('sync_token');
  }

  Future<void> updateConnection(String ip, int port, String token) async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = 'http://$ip:$port';
    _syncToken = token;
    await prefs.setString('api_base_url', _baseUrl);
    await prefs.setString('sync_token', token);
  }

  Stream<dynamic> getWebSocketStream() {
    final wsUrl = _baseUrl.replaceFirst('http', 'ws');
    final token = _syncToken ?? 'localhost';
    final channel = WebSocketChannel.connect(
      Uri.parse('$wsUrl/ws/$token'),
    );
    return channel.stream;
  }

  Options _getOptions() {
    return Options(
      headers: {
        if (_syncToken != null) 'X-Sync-Token': _syncToken,
      },
    );
  }

  Future<String?> transcribeAudio(File audioFile, String language, String? apiKey) async {
    try {
      FormData formData = FormData.fromMap({
        "file": await MultipartFile.fromFile(audioFile.path, filename: "voice.wav"),
        "language": language,
        if (apiKey != null && apiKey.isNotEmpty) "api_key": apiKey,
      });

      Response response = await _dio.post(
        "$_baseUrl/transcribe",
        data: formData,
        options: _getOptions(),
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
    String chatId = 'default',
    String? image,
  }) async {
    try {
      Response response = await _dio.post(
        "$_baseUrl/query",
        data: {
          'query': query,
          'is_voice': isVoice,
          'language': language,
          'assistant_name': assistantName,
          'llm_provider': llmProvider,
          'llm_model': llmModel,
          'api_key': apiKey ?? "",
          'allow_web_search': allowWebSearch,
          'chat_id': chatId,
          'image': image,
        },
        options: _getOptions(),
      );

      if (response.statusCode == 200) {
        return response.data;
      }
    } catch (e) {
      debugPrint("Query error: $e");
    }
    return null;
  }

  Future<bool> uploadVoice(File voiceFile) async {
    try {
      FormData formData = FormData.fromMap({
        "file": await MultipartFile.fromFile(voiceFile.path, filename: "user_voice.wav"),
      });

      Response response = await _dio.post(
        "$_baseUrl/upload_voice",
        data: formData,
        options: _getOptions(),
      );

      if (response.statusCode == 200) {
        final data = response.data;
        return data['success'] == true;
      }
    } catch (e) {
      debugPrint("Voice upload error: $e");
    }
    return false;
  }

  Future<File?> getTtsAudio(String text, String language) async {
    try {
      Response response = await _dio.post(
        "$_baseUrl/tts",
        data: {"text": text, "language": language},
        options: Options(
          responseType: ResponseType.bytes,
          headers: _getOptions().headers,
        ),
      );

      if (response.statusCode == 200) {
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
  
  Future<List<dynamic>> getMemories() async {
    try {
      final res = await _dio.get("$_baseUrl/memories", options: _getOptions());
      return res.data['memories'];
    } catch (e) { return []; }
  }

  Future<bool> addMemory(String fact, String category) async {
    try {
      final res = await _dio.post(
        "$_baseUrl/memories",
        data: {"fact": fact, "category": category},
        options: _getOptions(),
      );
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("Add memory error: $e");
      return false;
    }
  }

  Future<void> deleteMemory(int id) async {
    try {
      await _dio.delete("$_baseUrl/memories/$id", options: _getOptions());
    } catch (e) { debugPrint("Delete memory error: $e"); }
  }

  Future<List<dynamic>> getAutomations() async {
    try {
      final res = await _dio.get("$_baseUrl/automations", options: _getOptions());
      return res.data['automations'];
    } catch (e) { return []; }
  }

  Future<void> addAutomation(Map<String, dynamic> data) async {
    try {
      await _dio.post("$_baseUrl/automations", data: data, options: _getOptions());
    } catch (e) { debugPrint("Add automation error: $e"); }
  }

  Future<void> deleteAutomation(int id) async {
    try {
      await _dio.delete("$_baseUrl/automations/$id", options: _getOptions());
    } catch (e) { debugPrint("Delete automation error: $e"); }
  }

  // New method to fetch plugins list
  Future<List<dynamic>> getPlugins() async {
    try {
      final res = await _dio.get("$_baseUrl/plugins", options: _getOptions());
      return res.data['plugins'];
    } catch (e) {
      debugPrint("Get plugins error: $e");
      return [];
    }
  }
  // Toggle plugin enabled status
  Future<void> togglePlugin(int id, bool enabled) async {
    try {
      await _dio.patch('$_baseUrl/plugins/$id', data: {'enabled': enabled}, options: _getOptions());
    } catch (e) {
      debugPrint('Toggle plugin error: $e');
    }
  }

  // ── Chat History ─────────────────────────────────────────────────────────

  Future<List<dynamic>> getChatSessions() async {
    try {
      final res = await _dio.get("$_baseUrl/chats", options: _getOptions());
      return res.data['chats'] ?? [];
    } catch (e) {
      debugPrint("Get chat sessions error: $e");
      return [];
    }
  }

  Future<List<dynamic>> getChatMessages(String chatId) async {
    try {
      final res = await _dio.get("$_baseUrl/chats/$chatId/messages", options: _getOptions());
      return res.data['messages'] ?? [];
    } catch (e) {
      debugPrint("Get chat messages error: $e");
      return [];
    }
  }

  Future<bool> deleteChat(String chatId) async {
    try {
      await _dio.delete("$_baseUrl/chats/$chatId", options: _getOptions());
      return true;
    } catch (e) {
      debugPrint("Delete chat error: $e");
      return false;
    }
  }

  Future<bool> uploadPetAnimation(File file, String state) async {
    try {
      FormData formData = FormData.fromMap({
        "file": await MultipartFile.fromFile(file.path, filename: file.path.split('/').last),
        "state": state,
      });

      Response response = await _dio.post(
        "$_baseUrl/upload_pet",
        data: formData,
        options: _getOptions(),
      );

      if (response.statusCode == 200) {
        final data = response.data;
        return data['success'] == true;
      }
    } catch (e) {
      debugPrint("Pet upload error: $e");
    }
    return false;
  }

  Future<Map<String, dynamic>?> runCommand(String command) async {
    try {
      Response response = await _dio.post(
        "$_baseUrl/run_command",
        data: {"command": command},
        options: _getOptions(),
      );
      if (response.statusCode == 200) {
        return response.data;
      }
    } catch (e) {
      debugPrint("Run command error: $e");
    }
    return null;
  }
}

