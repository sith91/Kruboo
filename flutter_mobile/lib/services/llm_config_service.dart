import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class LLMConfig {
  final String provider;
  final String model;
  final String apiKey;
  final double temperature;
  final double topP;
  final int maxTokens;
  final String systemPrompt;

  const LLMConfig({
    required this.provider,
    required this.model,
    required this.apiKey,
    this.temperature = 0.7,
    this.topP = 0.9,
    this.maxTokens = 1500,
    this.systemPrompt = '',
  });

  Map<String, String> toMap() => {
        'provider': provider,
        'model': model,
        'apiKey': apiKey,
        'temperature': temperature.toString(),
        'topP': topP.toString(),
        'maxTokens': maxTokens.toString(),
        'systemPrompt': systemPrompt,
      };

  factory LLMConfig.fromMap(Map<String, String> map) => LLMConfig(
        provider: map['provider'] ?? '',
        model: map['model'] ?? '',
        apiKey: map['apiKey'] ?? '',
        temperature: double.tryParse(map['temperature'] ?? '') ?? 0.7,
        topP: double.tryParse(map['topP'] ?? '') ?? 0.9,
        maxTokens: int.tryParse(map['maxTokens'] ?? '') ?? 1500,
        systemPrompt: map['systemPrompt'] ?? '',
      );
}

class LLMConfigService {
  static const _storage = FlutterSecureStorage();
  static const _prefix = 'llm_config_';

  Future<void> saveConfig(LLMConfig config) async {
    final map = config.toMap();
    for (final entry in map.entries) {
      await _storage.write(key: '$_prefix${entry.key}', value: entry.value);
    }
  }

  Future<LLMConfig?> loadConfig() async {
    final keys = [
      'provider',
      'model',
      'apiKey',
      'temperature',
      'topP',
      'maxTokens',
      'systemPrompt',
    ];
    final values = <String, String>{};
    for (final key in keys) {
      final value = await _storage.read(key: '$_prefix$key');
      if (value == null) return null; // any missing means config not set
      values[key] = value;
    }
    return LLMConfig.fromMap(values);
  }

  // Placeholder test connection – replace with real API call if needed
  Future<bool> testConnection(LLMConfig config) async {
    // TODO: implement real health‑check per provider
    return true;
  }
}
