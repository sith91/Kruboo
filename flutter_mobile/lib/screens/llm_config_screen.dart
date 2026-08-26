import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/llm_config_service.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart'; // Assuming a GlassContainer widget exists

class LLMConfigScreen extends StatefulWidget {
  const LLMConfigScreen({Key? key}) : super(key: key);

  @override
  _LLMConfigScreenState createState() => _LLMConfigScreenState();
}

class _LLMConfigScreenState extends State<LLMConfigScreen> {
  final _service = LLMConfigService();
  late LLMConfig _config;
  bool _isLoading = true;
  final _apiKeyController = TextEditingController();
  final _systemPromptController = TextEditingController();
  String _objectRecognitionMode = "cloud";

  final List<String> _providers = ['OpenAI', 'Claude', 'Deepseek', 'Grok', 'Local'];
  final Map<String, List<String>> _modelsPerProvider = {
    'OpenAI': ['gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo'],
    'Claude': ['claude-opus-4-5', 'claude-sonnet-4-5', 'claude-3-haiku'],
    'Deepseek': ['deepseek-chat', 'deepseek-coder'],
    'Grok': ['grok-3', 'grok-3-mini'],
    'Local': ['llama3', 'mistral', 'phi3'],
  };

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    final saved = await _service.loadConfig();
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _objectRecognitionMode = prefs.getString('object_recognition_mode') ?? 'cloud';
      _config = saved ??
          const LLMConfig(
            provider: 'OpenAI',
            model: 'gpt-4-turbo',
            apiKey: '',
          );
      _apiKeyController.text = _config.apiKey;
      _systemPromptController.text = _config.systemPrompt;
      _isLoading = false;
    });
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('object_recognition_mode', _objectRecognitionMode);
    final newConfig = LLMConfig(
      provider: _config.provider,
      model: _config.model,
      apiKey: _apiKeyController.text,
      temperature: _config.temperature,
      topP: _config.topP,
      maxTokens: _config.maxTokens,
      systemPrompt: _systemPromptController.text,
    );
    await _service.saveConfig(newConfig);
    Navigator.of(context).pop();
  }

  Future<void> _testConnection() async {
    final testConfig = LLMConfig(
      provider: _config.provider,
      model: _config.model,
      apiKey: _apiKeyController.text,
    );
    final ok = await _service.testConnection(testConfig);
    final msg = ok ? 'Connection successful!' : 'Connection failed.';
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      appBar: AppBar(title: const Text('LLM Configuration'), backgroundColor: AppTheme.background),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Provider
              GlassContainer(
                child: DropdownButtonFormField<String>(
                  decoration: const InputDecoration(labelText: 'LLM Provider'),
                  value: _config.provider,
                  items: _providers.map((p) => DropdownMenuItem(value: p, child: Text(p))).toList(),
                  onChanged: (v) => setState(() {
                    _config = LLMConfig(
                      provider: v!,
                      model: _modelsPerProvider[v]!.first,
                      apiKey: _apiKeyController.text,
                      temperature: _config.temperature,
                      topP: _config.topP,
                      maxTokens: _config.maxTokens,
                      systemPrompt: _config.systemPrompt,
                    );
                  }),
                ),
              ),
              const SizedBox(height: 12),
              // Model
              GlassContainer(
                child: DropdownButtonFormField<String>(
                  decoration: const InputDecoration(labelText: 'Model'),
                  value: _config.model,
                  items: _modelsPerProvider[_config.provider]!
                      .map((m) => DropdownMenuItem(value: m, child: Text(m)))
                      .toList(),
                  onChanged: (v) => setState(() {
                    _config = LLMConfig(
                      provider: _config.provider,
                      model: v!,
                      apiKey: _apiKeyController.text,
                      temperature: _config.temperature,
                      topP: _config.topP,
                      maxTokens: _config.maxTokens,
                      systemPrompt: _config.systemPrompt,
                    );
                  }),
                ),
              ),
              const SizedBox(height: 12),
              // API Key
              GlassContainer(
                child: TextFormField(
                  controller: _apiKeyController,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'API Key'),
                ),
              ),
              const SizedBox(height: 12),
              // Object Recognition Mode
              GlassContainer(
                child: DropdownButtonFormField<String>(
                  decoration: const InputDecoration(labelText: 'Object Recognition Mode'),
                  value: _objectRecognitionMode.toLowerCase() == 'local' ? 'Local' : 'Cloud',
                  items: ['Cloud', 'Local'].map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
                  onChanged: (v) => setState(() {
                    _objectRecognitionMode = v!.toLowerCase();
                  }),
                ),
              ),
              const SizedBox(height: 12),
              // Advanced Settings
              ExpansionTile(
                title: Text('Advanced Settings', style: GoogleFonts.inter()),
                children: [
                  // Temperature
                  ListTile(
                    title: Text('Temperature', style: GoogleFonts.inter()),
                    subtitle: Slider(
                      value: _config.temperature,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: _config.temperature.toStringAsFixed(2),
                      onChanged: (v) => setState(() {
                        _config = LLMConfig(
                          provider: _config.provider,
                          model: _config.model,
                          apiKey: _apiKeyController.text,
                          temperature: v,
                          topP: _config.topP,
                          maxTokens: _config.maxTokens,
                          systemPrompt: _config.systemPrompt,
                        );
                      }),
                    ),
                  ),
                  // Top‑p
                  ListTile(
                    title: Text('Top‑p', style: GoogleFonts.inter()),
                    subtitle: Slider(
                      value: _config.topP,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: _config.topP.toStringAsFixed(2),
                      onChanged: (v) => setState(() {
                        _config = LLMConfig(
                          provider: _config.provider,
                          model: _config.model,
                          apiKey: _apiKeyController.text,
                          temperature: _config.temperature,
                          topP: v,
                          maxTokens: _config.maxTokens,
                          systemPrompt: _config.systemPrompt,
                        );
                      }),
                    ),
                  ),
                  // Max Tokens
                  ListTile(
                    title: Text('Max Tokens', style: GoogleFonts.inter()),
                    trailing: SizedBox(
                      width: 80,
                      child: TextFormField(
                        initialValue: _config.maxTokens.toString(),
                        keyboardType: TextInputType.number,
                        onChanged: (val) => setState(() {
                          final parsed = int.tryParse(val) ?? _config.maxTokens;
                          _config = LLMConfig(
                            provider: _config.provider,
                            model: _config.model,
                            apiKey: _apiKeyController.text,
                            temperature: _config.temperature,
                            topP: _config.topP,
                            maxTokens: parsed,
                            systemPrompt: _config.systemPrompt,
                          );
                        }),
                      ),
                    ),
                  ),
                  // System Prompt
                  Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: GlassContainer(
                      child: TextFormField(
                        controller: _systemPromptController,
                        maxLines: 3,
                        decoration: const InputDecoration(labelText: 'System Prompt'),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  ElevatedButton(
                    onPressed: _testConnection,
                    child: const Text('Test Connection'),
                  ),
                  ElevatedButton(
                    onPressed: _save,
                    child: const Text('Save'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
