import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';   // MethodChannel
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'screens/automation_screen.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'theme/app_theme.dart';
import 'widgets/orb_widget.dart';
import 'services/api_service.dart';
import 'screens/memory_screen.dart';
import 'screens/plugin_screen.dart';
import 'screens/conversation_screen.dart';
import 'services/voice_trigger_service.dart';
import 'screens/persona_screen.dart';
import 'services/llm_config_service.dart';
import 'services/persona_service.dart';
import 'models/persona.dart';
import 'screens/chat_history_screen.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';

void main() {
  runApp(const AssistantApp());
}

class AssistantApp extends StatefulWidget {
  const AssistantApp({Key? key}) : super(key: key);

  @override
  _AssistantAppState createState() => _AssistantAppState();
}

class _AssistantAppState extends State<AssistantApp> {
  final VoiceTriggerService _voiceService = VoiceTriggerService();
  StreamSubscription? _wakeSub;

  @override
  void initState() {
    super.initState();
    _initVoice();
  }

  Future<void> _initVoice() async {
    await _voiceService.init();
    _wakeSub = _voiceService.onWakeWordDetected.listen((_) {
      if (mounted) {
        Navigator.of(context).pushNamed('/conversation');
      }
    });
    // Prompt user to configure LLM if not set
    final configService = LLMConfigService();
    final config = await configService.loadConfig();
    if (config == null && mounted) {
      Navigator.of(context).pushReplacementNamed('/llm-config');
    }
  }

  @override
  void dispose() {
    _wakeSub?.cancel();
    _voiceService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kruuboo',
      theme: AppTheme.darkTheme,
      home: const MainScreen(),
      routes: {
        '/plugins': (context) => PluginScreen(),
        '/conversation': (context) => ConversationScreen(),
      },
      debugShowCheckedModeBanner: false,
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({Key? key}) : super(key: key);

  @override
  _MainScreenState createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  final List<Map<String, dynamic>> _chatHistory = [
    {"id": "1", "title": "First Conversation"}
  ];
  String _activeChatId = "1";
  // A unique ID for this launch — gives a fresh conversation each session
  // while preserving all previous messages in the DB under their own chat_id.
  final String _sessionChatId = DateTime.now().millisecondsSinceEpoch.toString();

  bool _isLoading = false;
  bool _showChat = false;
  OrbState _orbState = OrbState.idle;
  
  final ApiService _apiService = ApiService();
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  final FlutterTts _flutterTts = FlutterTts();
  final SpeechToText _speechToText = SpeechToText();
  bool _speechEnabled = false;

  // Configuration
  String _assistantName = "Kruuboo";
  String _language = "English";
  String _llmProvider = "OpenAI";
  String _llmModel = "gpt-4";
  String _apiKey = "";
  String _sttProvider = "local";
  bool _webSearchEnabled = true;
  bool _backgroundListening = false;
  int _selectedIndex = 0;
  String _activePersonaId = "";

  Process? _pythonProcess;
  StreamSubscription? _wsSubscription;
  String? _pendingImageBase64;

  Future<void> _captureImage({String? triggerAction, bool isVoice = false}) async {
    final picker = ImagePicker();
    try {
      final XFile? image = await picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 800,
        maxHeight: 600,
        imageQuality: 85,
      );
      if (image != null) {
        final bytes = await image.readAsBytes();
        final base64Img = base64Encode(bytes);
        setState(() {
          _pendingImageBase64 = base64Img;
          _showChat = true;
        });
        if (triggerAction != null) {
          if (triggerAction == 'visual_interpreter') {
            _sendMessage("", isVoice: isVoice);
          } else if (triggerAction == 'object_recognition') {
            final prefs = await SharedPreferences.getInstance();
            final mode = prefs.getString('object_recognition_mode') ?? 'cloud';
            if (mode == 'local') {
              setState(() {
                _isLoading = true;
                if (isVoice) _orbState = OrbState.thinking;
              });
              try {
                final String detected = await _backendChannel.invokeMethod<String>('detectObjects', {'image': base64Img}) ?? "No objects detected.";
                setState(() {
                  _messages.add({"role": "user", "content": "[Local Object Detection]"});
                  _messages.add({"role": "assistant", "content": detected});
                  _isLoading = false;
                  if (isVoice) {
                    _orbState = OrbState.speaking;
                    _speak(detected);
                  } else {
                    _orbState = OrbState.idle;
                  }
                  _pendingImageBase64 = null;
                });
              } catch (e) {
                debugPrint("Local detection failed: $e");
                setState(() {
                  _isLoading = false;
                  _orbState = OrbState.idle;
                });
              }
            } else {
              _sendMessage("Identify and list the objects you see in this image.", isVoice: isVoice);
            }
          }
        }
      }
    } catch (e) {
      debugPrint("Failed to snap photo: $e");
    }
  }

  Widget _buildImagePreviewThumbnail() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      alignment: Alignment.centerLeft,
      child: Stack(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Image.memory(
              base64Decode(_pendingImageBase64!),
              width: 60,
              height: 60,
              fit: BoxFit.cover,
            ),
          ),
          Positioned(
            right: 0,
            top: 0,
            child: GestureDetector(
              onTap: () => setState(() => _pendingImageBase64 = null),
              child: Container(
                decoration: const BoxDecoration(
                  color: Colors.black54,
                  shape: BoxShape.circle,
                ),
                padding: const EdgeInsets.all(2),
                child: const Icon(Icons.close, size: 12, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _loadSettings();
    _startPythonBackend();
    _initTts();
  }

  void _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final configService = LLMConfigService();
    final config = await configService.loadConfig();
    setState(() {
      _backgroundListening = prefs.getBool('background_listening') ?? false;
      _activePersonaId = prefs.getString('active_persona_id') ?? '';
      if (config != null) {
        final validProviders = ["OpenAI", "Claude", "Deepseek", "Gork", "Anthoproc", "Local"];
        _llmProvider = validProviders.firstWhere(
          (e) => e.toLowerCase() == config.provider.toLowerCase(),
          orElse: () => "OpenAI",
        );
        _llmModel = config.model;
        _apiKey = config.apiKey;
      }
    });
    if (_backgroundListening) {
      _updateBackgroundListening(true);
    }
  }

  void _updateBackgroundListening(bool enabled) async {
    if (Platform.isAndroid) {
      try {
        await _backendChannel.invokeMethod('enableBackgroundListening', {'enabled': enabled});
      } catch (e) {
        debugPrint("[Backend] Failed to update background listening: $e");
      }
    }
  }

  void _initWebSocket() {
    _wsSubscription?.cancel();
    _wsSubscription = _apiService.getWebSocketStream().listen((data) {
      try {
        final event = json.decode(data);
        if (event['type'] == 'message') {
          final role = event['role'];
          final content = event['content'];
          
          // Simple duplicate check: avoid adding if it's the same as the last message
          if (_messages.isNotEmpty && _messages.last['content'] == content) {
             return;
          }

          setState(() {
            _messages.add({"role": role, "content": content});
            if (role == 'user') _showChat = true;
          });
        }
      } catch (e) {
        debugPrint("WS Error: $e");
      }
    }, onError: (err) {
      debugPrint("WS Connection Error: $err");
      // Retry after 5 seconds
      Future.delayed(const Duration(seconds: 5), _initWebSocket);
    });
  }

  void _initTts() async {
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);
    _updateTtsLanguage();
  }

  void _updateTtsLanguage() async {
    if (_language == "English") {
      await _flutterTts.setLanguage("en-US");
    } else if (_language == "Sinhala") {
      await _flutterTts.setLanguage("si-LK");
    } else if (_language == "Tamil") {
      await _flutterTts.setLanguage("ta-IN");
    }
  }

  // ── Backend channel (Android: Chaquopy ForegroundService) ───────────────
  static const _backendChannel = MethodChannel('com.kruuboo/backend');

  void _startPythonBackend() async {
    if (Platform.isAndroid) {
      // On Android: delegate to Kotlin BackendService which runs Python via Chaquopy
      try {
        final result = await _backendChannel.invokeMethod<String>('startBackend');
        debugPrint("[Backend] Android service: $result");
        _waitForBackendReady();
      } on MissingPluginException {
        debugPrint("[Backend] MethodChannel not available — running without embedded backend");
      } catch (e) {
        debugPrint("[Backend] Failed to start Android service: $e");
      }
    } else {
      // Desktop fallback (macOS / Linux): spawn Python process directly
      try {
        _pythonProcess = await Process.start(
          'python3',
          ['main.py'],
          workingDirectory: '../python_backend',
        );
        _pythonProcess?.stdout.transform(utf8.decoder).listen((d) => debugPrint("[Backend] $d"));
        _pythonProcess?.stderr.transform(utf8.decoder).listen((d) => debugPrint("[Backend ERR] $d"));
        _waitForBackendReady();
      } catch (e) {
        debugPrint("[Backend] Could not start desktop process: $e");
      }
    }
  }

  Future<void> _waitForBackendReady() async {
    setState(() => _orbState = OrbState.thinking);
    for (int i = 0; i < 20; i++) {
      await Future.delayed(const Duration(seconds: 1));
      try {
        final res = await http.get(Uri.parse('http://127.0.0.1:8000/')).timeout(
          const Duration(seconds: 1));
        if (res.statusCode == 200) {
          _initWebSocket();
          setState(() => _orbState = OrbState.idle);
          _requestScreenCapturePermission();
          return;
        }
      } catch (_) {}
    }
    debugPrint('[Backend] Timeout — backend may not have started');
    setState(() => _orbState = OrbState.idle);
  }

  void _requestScreenCapturePermission() async {
    if (Platform.isAndroid) {
      try {
        final bool hasPermission = await _backendChannel.invokeMethod<bool>('hasScreenCapturePermission') ?? false;
        if (!hasPermission) {
          await _backendChannel.invokeMethod('requestScreenCapture');
        }
      } catch (e) {
        debugPrint("Error requesting screen capture permission: $e");
      }
    }
  }

  @override
  void dispose() {
    _pythonProcess?.kill();
    _wsSubscription?.cancel();
    _controller.dispose();
    _recorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _handleOrbTap() async {
    if (_orbState == OrbState.listening) {
      _stopRecording();
    } else if (_orbState == OrbState.speaking) {
      _stopSpeaking();
    } else {
      _startRecording();
    }
  }

  Future<void> _stopSpeaking() async {
    await _flutterTts.stop();
    setState(() {
      _orbState = OrbState.idle;
    });
  }

  Future<void> _startRecording() async {
    if (Platform.isAndroid) {
      if (!_speechEnabled) {
        _speechEnabled = await _speechToText.initialize(
          onError: (val) => debugPrint('STT Error: $val'),
          onStatus: (val) => debugPrint('STT Status: $val'),
        );
      }
      
      if (_speechEnabled) {
        setState(() {
          _orbState = OrbState.listening;
        });
        
        await _speechToText.listen(
          onResult: (result) {
            if (result.finalResult && result.recognizedWords.isNotEmpty) {
              _sendMessage(result.recognizedWords, isVoice: true);
            }
          },
          localeId: _language == 'Sinhala' ? 'si-LK' : _language == 'Tamil' ? 'ta-IN' : 'en-US',
        );
      } else {
        debugPrint("Speech recognition not available");
      }
    } else {
      if (await _recorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        final path = '${dir.path}/voice_input.wav';
        
        const config = RecordConfig(encoder: AudioEncoder.wav);
        await _recorder.start(config, path: path);
        
        setState(() {
          _orbState = OrbState.listening;
        });
      }
    }
  }

  Future<void> _stopRecording() async {
    if (Platform.isAndroid) {
      await _speechToText.stop();
      setState(() {
        _orbState = OrbState.thinking;
      });
    } else {
      final path = await _recorder.stop();
      setState(() {
        _orbState = OrbState.thinking;
      });

      if (path != null) {
        final file = File(path);
        final transcription = await _apiService.transcribeAudio(file, _language, _sttProvider == 'whisper' ? _apiKey : null);
        
        if (transcription != null && transcription.isNotEmpty) {
          _sendMessage(transcription, isVoice: true);
        } else {
          setState(() => _orbState = OrbState.idle);
        }
      } else {
        setState(() => _orbState = OrbState.idle);
      }
    }
  }

  void _sendMessage(String text, {bool isVoice = false}) async {
    if (text.trim().isEmpty && _pendingImageBase64 == null) return;

    String queryText = text;
    if (queryText.isEmpty && _pendingImageBase64 != null) {
      queryText = "Describe this image";
    }

    String displayPrompt = queryText;
    final imagePayload = _pendingImageBase64;
    if (imagePayload != null) {
      displayPrompt = "[Sent an Image] $queryText";
    }

    setState(() {
      _messages.add({"role": "user", "content": displayPrompt});
      _isLoading = true;
      if (isVoice) _orbState = OrbState.thinking;
      _pendingImageBase64 = null;
    });
    _controller.clear();

    final response = await _apiService.sendQuery(
      query: queryText,
      isVoice: isVoice,
      language: _language,
      assistantName: _assistantName,
      llmProvider: _llmProvider,
      llmModel: _llmModel,
      apiKey: _apiKey,
      allowWebSearch: _webSearchEnabled,
      chatId: _sessionChatId,
      image: imagePayload,
    );

    if (response != null) {
      final botResponse = response['response'];
      final action = response['action_taken'];
      setState(() {
        _messages.add({"role": "assistant", "content": botResponse});
        if (isVoice) _orbState = OrbState.speaking;
      });

      // Prefer backend TTS for better quality (especially for Sinhala)
      if (isVoice) {
         _speak(botResponse);
      }

      if (action == 'visual_interpreter') {
         Future.delayed(const Duration(milliseconds: 1000), () {
            _captureImage(triggerAction: 'visual_interpreter', isVoice: isVoice);
         });
      } else if (action == 'object_recognition') {
         Future.delayed(const Duration(milliseconds: 1000), () {
            _captureImage(triggerAction: 'object_recognition', isVoice: isVoice);
         });
      }
    } else {
      setState(() {
        _messages.add({"role": "assistant", "content": "Brain connection failed."});
        _orbState = OrbState.idle;
      });
    }

    setState(() {
      _isLoading = false;
      if (!isVoice) _orbState = OrbState.idle;
    });
  }

  Future<void> _speak(String text) async {
    // Attempt backend TTS first
    final file = await _apiService.getTtsAudio(text, _language);
    if (file != null) {
      await _audioPlayer.play(DeviceFileSource(file.path));
      _audioPlayer.onPlayerComplete.listen((_) {
        setState(() => _orbState = OrbState.idle);
      });
    } else {
      // Fallback to local TTS
      await _flutterTts.speak(text);
      _flutterTts.setCompletionHandler(() {
        setState(() => _orbState = OrbState.idle);
      });
    }
  }

  void _openSettings() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => _SettingsPage(
          initialName: _assistantName,
          initialLang: _language,
          initialProvider: _llmProvider,
          initialModel: _llmModel,
          initialKey: _apiKey,
          initialSttProvider: _sttProvider,
          initialBackgroundListening: _backgroundListening,
          apiService: _apiService,
          onLinkDevice: _initWebSocket,
          activePersonaId: _activePersonaId,
          onSave: (name, lang, provider, model, key, sttProvider, bgListening, activePersonaId) async {
            setState(() {
              _assistantName = name;
              _language = lang;
              _llmProvider = provider;
              _llmModel = model;
              _apiKey = key;
              _sttProvider = sttProvider;
              _backgroundListening = bgListening;
              _activePersonaId = activePersonaId;
            });
            final configService = LLMConfigService();
            await configService.saveConfig(LLMConfig(
              provider: provider,
              model: model,
              apiKey: key,
            ));
            final prefs = await SharedPreferences.getInstance();
            await prefs.setBool('background_listening', bgListening);
            await prefs.setString('active_persona_id', activePersonaId);
            _updateBackgroundListening(bgListening);
            _updateTtsLanguage();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      bottomNavigationBar: MediaQuery.of(context).size.width <= 700
          ? BottomNavigationBar(
              backgroundColor: AppTheme.background,
              selectedItemColor: AppTheme.accent,
              unselectedItemColor: Colors.white70,
              currentIndex: _selectedIndex,
              onTap: (index) {
                setState(() {
                  _selectedIndex = index;
                });
                if (index == 0) {
                  setState(() => _showChat = true);
                } else if (index == 1) {
                  _openSettings();
                } else if (index == 2) {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PluginScreen()));
                }
              },
              items: const [
                BottomNavigationBarItem(icon: Icon(Icons.chat_bubble_outline), label: 'Chat'),
                BottomNavigationBarItem(icon: Icon(Icons.settings_outlined), label: 'Settings'),
                BottomNavigationBarItem(icon: Icon(Icons.extension_outlined), label: 'Plugins'),
              ],
            )
          : null,
      body: Row(
        children: [
          // Sidebar (only on Desktop or if needed)
          if (MediaQuery.of(context).size.width > 700)
            Container(
              width: 240,
              decoration: const BoxDecoration(
                border: Border(right: BorderSide(color: AppTheme.border, width: 0.5)),
              ),
              child: _buildSidebar(),
            ),
          Expanded(
            child: Stack(
              children: [
                // Background
                Container(color: AppTheme.background),
                // Content
                Column(
                  children: [
                    _buildHeader(),
                    Expanded(
                      child: _showChat ? _buildChatView() : _buildOrbView(),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          if (_showChat)
            IconButton(
              icon: const Icon(Icons.arrow_back_ios_new, size: 20),
              onPressed: () => setState(() => _showChat = false),
            )
          else
            const SizedBox(width: 40),
          
          Text(
            _showChat ? "Conversation" : _assistantName.toUpperCase(),
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              letterSpacing: 2,
              color: AppTheme.textDim,
            ),
          ),
          
          const SizedBox(width: 40),
        ],
      ),
    );
  }

  Widget _buildSidebar() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 40),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Text("CHATS", style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textDim, letterSpacing: 1.5)),
        ),
        const SizedBox(height: 20),
        Expanded(
          child: ListView.builder(
            itemCount: _chatHistory.length,
            itemBuilder: (context, index) {
              final chat = _chatHistory[index];
              final isActive = chat['id'] == _activeChatId;
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                decoration: BoxDecoration(
                  color: isActive ? AppTheme.surfaceHover : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: isActive ? AppTheme.accent.withOpacity(0.2) : Colors.transparent),
                ),
                child: ListTile(
                  dense: true,
                  leading: const Icon(Icons.chat_outlined, size: 16),
                  title: Text(chat['title'], style: GoogleFonts.inter(fontSize: 13, color: isActive ? AppTheme.text : AppTheme.textDim)),
                  onTap: () => setState(() {
                    _activeChatId = chat['id'];
                    _showChat = true;
                  }),
                ),
              );
            },
          ),
        ),
        _buildSidebarFooter(),
      ],
    );
  }

  Widget _buildSidebarFooter() {
    return Container(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const Divider(color: AppTheme.border),
          const SizedBox(height: 6),
          InkWell(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ChatHistoryScreen(apiService: _apiService),
              ),
            ),
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
              child: Row(
                children: [
                  const Icon(Icons.history_rounded, size: 16, color: AppTheme.textDim),
                  const SizedBox(width: 10),
                  Text('Chat History',
                      style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textDim)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              CircleAvatar(
                radius: 12,
                backgroundColor: AppTheme.accent.withOpacity(0.2),
                child: const Text("S", style: TextStyle(fontSize: 10, color: AppTheme.accent)),
              ),
              const SizedBox(width: 10),
              Text("Sithija", style: GoogleFonts.inter(fontSize: 12, color: AppTheme.text)),
            ],
          )
        ],
      ),
    );
  }


  Widget _buildOrbView() {
    return Center(
      key: const ValueKey("orb"),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(flex: 2),
          OrbWidget(
            state: _orbState,
            apiService: _apiService,
            onTap: _handleOrbTap,
            onLongPress: () => setState(() => _showChat = true),
          ),
          const SizedBox(height: 50),
          Text(
            _orbState == OrbState.listening ? "LISTENING..." : 
            _orbState == OrbState.thinking ? "THINKING..." : "KRUUBOO",
            style: GoogleFonts.inter(
              letterSpacing: 4,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppTheme.textDim,
            ),
          ),
          const Spacer(flex: 3),
          _buildQuickActions(),
        ],
      ),
    );
  }

  Widget _buildQuickActions() {
    return const SizedBox.shrink();
  }

  Widget _buildChatView() {
    return Column(
      key: const ValueKey("chat"),
      children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            itemCount: _messages.length,
            itemBuilder: (context, index) {
              final msg = _messages[index];
              final isUser = msg['role'] == 'user';
              return _ChatBubble(message: msg['content'], isUser: isUser, apiService: _apiService);
            },
          ),
        ),
        if (_pendingImageBase64 != null) _buildImagePreviewThumbnail(),
        if (_isLoading)
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: LinearProgressIndicator(backgroundColor: Colors.transparent, color: AppTheme.accent),
          ),
        _buildChatInput(),
      ],
    );
  }

  Widget _buildChatInput() {
    return Container(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.camera_alt_outlined, color: AppTheme.accent),
            onPressed: _captureImage,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: GlassContainer(
              borderRadius: 30,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: TextField(
                controller: _controller,
                onSubmitted: (val) => _sendMessage(val),
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: "Message $_assistantName...",
                  hintStyle: const TextStyle(color: AppTheme.textDim, fontSize: 14),
                  border: InputBorder.none,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          FloatingActionButton.small(
            onPressed: () => _sendMessage(_controller.text),
            backgroundColor: AppTheme.accent,
            child: const Icon(Icons.send_rounded, size: 18),
          )
        ],
      ),
    );
  }
}

class _CommandExecutionCard extends StatefulWidget {
  final String command;
  final ApiService apiService;

  const _CommandExecutionCard({Key? key, required this.command, required this.apiService}) : super(key: key);

  @override
  _CommandExecutionCardState createState() => _CommandExecutionCardState();
}

class _CommandExecutionCardState extends State<_CommandExecutionCard> {
  bool _isExecuting = false;
  bool _hasExecuted = false;
  bool _success = false;
  String _stdout = "";
  String _stderr = "";
  String _error = "";

  void _execute() async {
    setState(() {
      _isExecuting = true;
    });

    final res = await widget.apiService.runCommand(widget.command);
    if (!mounted) return;

    if (res != null) {
      setState(() {
        _isExecuting = false;
        _hasExecuted = true;
        _success = res['success'] == true;
        _stdout = res['stdout'] ?? "";
        _stderr = res['stderr'] ?? "";
        _error = res['error'] ?? "";
      });
    } else {
      setState(() {
        _isExecuting = false;
        _hasExecuted = true;
        _success = false;
        _error = "Connection failed. Could not reach backend.";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.4),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.terminal_rounded, color: Colors.white, size: 18),
              const SizedBox(width: 8),
              Text(
                "Execute Command",
                style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF111111),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0x3300FF87)),
            ),
            child: Text(
              widget.command,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Color(0xFF00FF87)),
            ),
          ),
          const SizedBox(height: 12),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: _hasExecuted 
                  ? (_success ? const Color(0xFF28A745) : const Color(0xFFDC3545)) 
                  : AppTheme.accent,
              foregroundColor: Colors.white,
              minimumSize: const Size(double.infinity, 38),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: (_isExecuting || _hasExecuted) ? null : _execute,
            child: Text(
              _isExecuting 
                  ? "Executing..." 
                  : (_hasExecuted 
                      ? (_success ? "Executed Successfully" : "Execution Failed") 
                      : "Approve & Execute"),
              style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 12),
            ),
          ),
          if (_hasExecuted) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              maxHeight: 150,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF111111),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white10),
              ),
              child: SingleChildScrollView(
                child: Text(
                  _success 
                      ? (_stdout.isNotEmpty ? _stdout : "(Executed successfully, no output)") 
                      : ("Error: $_error\n$_stderr"),
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 11, 
                    color: _success ? const Color(0xFF00FF87) : const Color(0xFFFF4C4C),
                  ),
                ),
              ),
            ),
          ]
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  final ApiService apiService;

  const _ChatBubble({Key? key, required this.message, required this.isUser, required this.apiService}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final bool isProposedCommand = !isUser && message.startsWith("PROPOSED_COMMAND: ");
    final String cleanMessage = isProposedCommand ? message.substring("PROPOSED_COMMAND: ".length).trim() : message;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            if (isProposedCommand)
              ConstrainedBox(
                constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                child: _CommandExecutionCard(command: cleanMessage, apiService: apiService),
              )
            else
              GlassContainer(
                borderRadius: 16,
                color: isUser ? AppTheme.accent.withOpacity(0.15) : AppTheme.surface,
                border: Border.all(color: isUser ? AppTheme.accent.withOpacity(0.3) : AppTheme.border, width: 0.5),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.65),
                  child: Text(
                    message,
                    style: GoogleFonts.inter(fontSize: 14, color: AppTheme.text, height: 1.5),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _QuickAction({Key? key, required this.icon, required this.label, required this.onTap}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          children: [
            GlassContainer(
              width: 50,
              height: 50,
              borderRadius: 12,
              child: Icon(icon, color: AppTheme.text, size: 20),
            ),
            const SizedBox(height: 8),
            Text(label, style: GoogleFonts.inter(fontSize: 10, color: AppTheme.textDim, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
    );
  }
}

class _SettingsPage extends StatefulWidget {
  final String initialName;
  final String initialLang;
  final String initialProvider;
  final String initialModel;
  final String initialKey;
  final String initialSttProvider;
  final bool initialBackgroundListening;
  final String activePersonaId;
  final ApiService apiService;
  final VoidCallback onLinkDevice;
  final Function(String, String, String, String, String, String, bool, String) onSave;

  const _SettingsPage({
    Key? key,
    required this.initialName,
    required this.initialLang,
    required this.initialProvider,
    required this.initialModel,
    required this.initialKey,
    required this.initialSttProvider,
    required this.initialBackgroundListening,
    required this.activePersonaId,
    required this.apiService,
    required this.onLinkDevice,
    required this.onSave,
  }) : super(key: key);

  @override
  _SettingsPageState createState() => _SettingsPageState();
}

class _SettingsPageState extends State<_SettingsPage> {
  late String _name, _lang, _provider, _model, _key, _sttProvider;
  late bool _bgListening;
  String _activePersonaId = '';
  List<Persona> _personas = [];

  @override
  void initState() {
    super.initState();
    _name = widget.initialName;
    _activePersonaId = widget.activePersonaId;

    final validLangs = ["English", "Sinhala", "Tamil"];
    _lang = validLangs.firstWhere((e) => e.toLowerCase() == widget.initialLang.toLowerCase(), orElse: () => validLangs.first);

    final validProviders = ["OpenAI", "Claude", "Deepseek", "Grok", "Local"];
    _provider = validProviders.firstWhere((e) => e.toLowerCase() == widget.initialProvider.toLowerCase(), orElse: () => validProviders.first);

    final validStt = ["local", "whisper"];
    _sttProvider = validStt.firstWhere((e) => e.toLowerCase() == widget.initialSttProvider.toLowerCase(), orElse: () => validStt.first);

    _model = widget.initialModel;
    _key = widget.initialKey;
    _bgListening = widget.initialBackgroundListening;
    _loadPersonas();
  }

  Future<void> _loadPersonas() async {
    final personas = await PersonaService().getPersonas();
    if (!mounted) return;
    setState(() {
      _personas = personas;
      if (_activePersonaId.isNotEmpty && !personas.any((p) => p.id == _activePersonaId)) {
        _activePersonaId = '';
      }
    });
  }

  void _save() {
    widget.onSave(_name, _lang, _provider, _model, _key, _sttProvider, _bgListening, _activePersonaId);
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        title: Text(
          'SETTINGS',
          style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 2, color: AppTheme.textDim),
        ),
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          TextButton(
            onPressed: _save,
            child: Text('Save', style: GoogleFonts.inter(color: AppTheme.accent, fontWeight: FontWeight.w600)),
          ),
        ],
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(0.5),
          child: Container(height: 0.5, color: AppTheme.border),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        children: [
          // ── General ────────────────────────────────────────────
          _sectionHeader('GENERAL'),
          _buildField("Assistant Name", _name, (val) => _name = val),
          _buildDropdown("Language", _lang, ["English", "Sinhala", "Tamil"], (val) => setState(() => _lang = val!)),
          const SizedBox(height: 24),

          // ── AI Engine ────────────────────────────────────────────
          _sectionHeader('AI ENGINE'),
          _buildDropdown("LLM Provider", _provider, ["OpenAI", "Claude", "Deepseek", "Grok", "Local"], (val) => setState(() => _provider = val!)),
          _buildField("Model Name", _model, (val) => _model = val),
          _buildField("API Key", _key, (val) => _key = val, obscure: true),
          _buildDropdown("STT Provider", _sttProvider, ["local", "whisper"], (val) => setState(() => _sttProvider = val!)),
          if (Platform.isAndroid)
            _buildSwitch("Background Voice Listening", _bgListening, (val) => setState(() => _bgListening = val)),
          const SizedBox(height: 24),

          // ── Identity & Assets ────────────────────────────────────
          _sectionHeader('IDENTITY & ASSETS'),
          _buildSettingsLink("UPLOAD VOICE SAMPLE (ELEVENLABS)", Icons.record_voice_over_outlined, () async {
            try {
              final result = await FilePicker.pickFiles(
                type: FileType.custom,
                allowedExtensions: ['wav', 'mp3'],
              );
              if (result != null && result.files.single.path != null) {
                final file = File(result.files.single.path!);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Uploading voice sample...")),
                );
                final ok = await widget.apiService.uploadVoice(file);
                if (ok) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Voice cloned successfully!"), backgroundColor: Colors.green),
                  );
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Upload failed. Verify API Key."), backgroundColor: Colors.red),
                  );
                }
              }
            } catch (e) {
              debugPrint("Voice clone error: $e");
            }
          }),
          _buildSettingsLink("UPLOAD IDLE PET (.GIF/.PNG)", Icons.pets, () => _pickAndUploadPet("idle")),
          _buildSettingsLink("UPLOAD LISTENING PET (.GIF/.PNG)", Icons.mic_none, () => _pickAndUploadPet("listening")),
          _buildSettingsLink("UPLOAD THINKING PET (.GIF/.PNG)", Icons.psychology, () => _pickAndUploadPet("thinking")),
          _buildSettingsLink("UPLOAD SPEAKING PET (.GIF/.PNG)", Icons.volume_up, () => _pickAndUploadPet("speaking")),
          const SizedBox(height: 24),

          // ── Persona ─────────────────────────────────────────────
          _sectionHeader('PERSONA'),
          if (_personas.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: DropdownButtonFormField<String>(
                value: _activePersonaId.isEmpty ? null : _activePersonaId,
                decoration: InputDecoration(
                  labelText: 'Active Persona',
                  labelStyle: const TextStyle(color: AppTheme.textDim, fontSize: 13),
                  filled: true,
                  fillColor: AppTheme.surface,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                ),
                dropdownColor: const Color(0xFF1C1C1E),
                style: const TextStyle(color: Colors.white, fontSize: 14),
                hint: const Text('None (default)', style: TextStyle(color: AppTheme.textDim, fontSize: 14)),
                items: [
                  const DropdownMenuItem<String>(value: '', child: Text('None (default)', style: TextStyle(color: AppTheme.textDim))),
                  ..._personas.map((p) => DropdownMenuItem<String>(
                    value: p.id,
                    child: Row(children: [
                      const Icon(Icons.person_outline, size: 16, color: AppTheme.accent),
                      const SizedBox(width: 8),
                      Text(p.name),
                    ]),
                  )),
                ],
                onChanged: (val) => setState(() => _activePersonaId = val ?? ''),
              ),
            ),
          _buildSettingsLink("MANAGE PERSONAS", Icons.person_add_outlined, () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => const PersonaScreen()))
                .then((_) => _loadPersonas());
          }),
          const SizedBox(height: 24),

          // ── Tools ────────────────────────────────────────────
          _sectionHeader('TOOLS & MEMORY'),
          _buildSettingsLink("CHAT HISTORY", Icons.history_rounded, () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => ChatHistoryScreen(apiService: widget.apiService)));
          }),
          _buildSettingsLink("MANAGE MEMORY", Icons.psychology_outlined, () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => MemoryScreen(apiService: widget.apiService)));
          }),
          _buildSettingsLink("DYNAMIC AUTOMATIONS", Icons.auto_fix_high_outlined, () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => AutomationScreen(apiService: widget.apiService)));
          }),
          _buildSettingsLink("PLUGINS", Icons.extension_outlined, () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => PluginScreen()));
          }),
          const SizedBox(height: 24),

          // ── Device ────────────────────────────────────────────
          _sectionHeader('DEVICE'),
          _buildSettingsLink("DEVICE PAIRING (P2P)", Icons.devices_other_rounded, () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => _DevicePairingPage(
                  apiService: widget.apiService,
                  onLinkDevice: widget.onLinkDevice,
                ),
              ),
            );
          }),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        title,
        style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.accent, letterSpacing: 1.5),
      ),
    );
  }

  Widget _buildSettingsLink(String label, IconData icon, VoidCallback onTap) {
    return ListTile(
      leading: Icon(icon, color: AppTheme.accent, size: 20),
      title: Text(label, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1)),
      trailing: const Icon(Icons.arrow_forward_ios, size: 12),
      onTap: onTap,
    );
  }

  Widget _buildField(String label, String value, Function(String) onChanged, {bool obscure = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        decoration: InputDecoration(labelText: label),
        controller: TextEditingController(text: value),
        onChanged: onChanged,
        obscureText: obscure,
      ),
    );
  }

  Widget _buildDropdown(String label, String value, List<String> items, Function(String?) onChanged) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DropdownButtonFormField<String>(
        value: value,
        decoration: InputDecoration(labelText: label),
        items: items.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
        onChanged: onChanged,
      ),
    );
  }

  Widget _buildSwitch(String label, bool value, Function(bool) onChanged) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SwitchListTile(
        title: Text(label, style: GoogleFonts.inter(fontSize: 13, color: AppTheme.text)),
        subtitle: Text("Say 'Kruuboo' in background (increases battery use)", style: GoogleFonts.inter(fontSize: 10, color: AppTheme.textDim)),
        value: value,
        onChanged: onChanged,
        activeColor: AppTheme.accent,
        contentPadding: EdgeInsets.zero,
      ),
    );
  }

  void _pickAndUploadPet(String state) async {
    try {
      final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['gif', 'png', 'jpg', 'jpeg', 'apng'],
      );
      if (result != null && result.files.single.path != null) {
        final file = File(result.files.single.path!);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Uploading $state pet animation...")),
        );
        final ok = await widget.apiService.uploadPetAnimation(file, state);
        if (!mounted) return;
        if (ok) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("$state pet uploaded successfully!"), backgroundColor: Colors.green),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Upload failed. Verify server connection."), backgroundColor: Colors.red),
          );
        }
      }
    } catch (e) {
      debugPrint("Pet upload error: $e");
    }
  }
}

class _ScannerScreen extends StatelessWidget {
  final Function(String) onScan;
  const _ScannerScreen({Key? key, required this.onScan}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Scan Pairing QR")),
      body: MobileScanner(
        onDetect: (capture) {
          final List<Barcode> barcodes = capture.barcodes;
          for (final barcode in barcodes) {
            if (barcode.rawValue != null) {
              onScan(barcode.rawValue!);
              break;
            }
          }
        },
      ),
    );
  }
}

class _DevicePairingPage extends StatefulWidget {
  final ApiService apiService;
  final VoidCallback onLinkDevice;

  const _DevicePairingPage({Key? key, required this.apiService, required this.onLinkDevice}) : super(key: key);

  @override
  _DevicePairingPageState createState() => _DevicePairingPageState();
}

class _DevicePairingPageState extends State<_DevicePairingPage> {
  void _openScanner(BuildContext context) async {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => _ScannerScreen(
          onScan: (data) async {
            try {
              final Map<String, dynamic> pairing = json.decode(data);
              await widget.apiService.updateConnection(
                pairing['ip'], 
                pairing['port'], 
                pairing['token']
              );
              widget.onLinkDevice(); // Refresh WS connection with new token/IP
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Device Linked Successfully!"), backgroundColor: Colors.green),
                );
                Navigator.pop(context); // Close scanner
                Navigator.pop(context); // Close pairing page
              }
            } catch (e) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Invalid QR Code"), backgroundColor: Colors.red),
              );
            }
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        title: Text(
          'DEVICE PAIRING',
          style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 2, color: AppTheme.textDim),
        ),
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Navigator.of(context).pop(),
        ),
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(0.5),
          child: Container(height: 0.5, color: AppTheme.border),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 30),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Spacer(),
            const Icon(Icons.devices_other_rounded, size: 80, color: AppTheme.accent),
            const SizedBox(height: 24),
            Text(
              "Pair with Desktop Assistant",
              style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 12),
            Text(
              "Connect to your desktop brain to offload heavy calculations and use custom LLMs and Vision settings.",
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(fontSize: 13, color: AppTheme.textDim, height: 1.5),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.border, width: 0.5),
              ),
              child: Text(
                "Current Backend: ${widget.apiService.baseUrl}",
                style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.white70),
              ),
            ),
            const Spacer(),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF25D366),
                foregroundColor: Colors.white,
                minimumSize: const Size(double.infinity, 50),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text("LINK NEW DEVICE (P2P)"),
              onPressed: () => _openScanner(context),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
