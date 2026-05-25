import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'theme/app_theme.dart';
import 'widgets/orb_widget.dart';
import 'services/api_service.dart';
import 'screens/memory_screen.dart';
import 'screens/automation_screen.dart';

void main() {
  runApp(const AssistantApp());
}

class AssistantApp extends StatelessWidget {
  const AssistantApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Nexus AI',
      theme: AppTheme.darkTheme,
      home: const MainScreen(),
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

  bool _isLoading = false;
  bool _showChat = false;
  OrbState _orbState = OrbState.idle;
  
  final ApiService _apiService = ApiService();
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  final FlutterTts _flutterTts = FlutterTts();
  
  // Configuration
  String _assistantName = "Nexus AI";
  String _language = "English";
  String _llmProvider = "openai";
  String _llmModel = "gpt-4";
  String _apiKey = "";
  bool _webSearchEnabled = true;

  Process? _pythonProcess;
  StreamSubscription? _wsSubscription;

  @override
  void initState() {
    super.initState();
    _startPythonBackend();
    _initTts();
    _initWebSocket();
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

  void _startPythonBackend() async {
    try {
      // Note: This logic assumes the backend exists in the parent directory as per the plan
      _pythonProcess = await Process.start(
        'python',
        ['main.py'],
        workingDirectory: '../python_backend',
      );

      _pythonProcess?.stdout.transform(utf8.decoder).listen((data) => debugPrint("Backend: $data"));
      _pythonProcess?.stderr.transform(utf8.decoder).listen((data) => debugPrint("Backend Error: $data"));
    } catch (e) {
      debugPrint("Could not start backend: $e");
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
    } else {
      _startRecording();
    }
  }

  Future<void> _startRecording() async {
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

  Future<void> _stopRecording() async {
    final path = await _recorder.stop();
    setState(() {
      _orbState = OrbState.thinking;
    });

    if (path != null) {
      final file = File(path);
      final transcription = await _apiService.transcribeAudio(file, _language, _apiKey);
      
      if (transcription != null && transcription.isNotEmpty) {
        _sendMessage(transcription, isVoice: true);
      } else {
        setState(() => _orbState = OrbState.idle);
      }
    } else {
      setState(() => _orbState = OrbState.idle);
    }
  }

  void _sendMessage(String text, {bool isVoice = false}) async {
    if (text.trim().isEmpty) return;

    setState(() {
      _messages.add({"role": "user", "content": text});
      _isLoading = true;
      if (isVoice) _orbState = OrbState.thinking;
    });
    _controller.clear();

    final response = await _apiService.sendQuery(
      query: text,
      isVoice: isVoice,
      language: _language,
      assistantName: _assistantName,
      llmProvider: _llmProvider,
      llmModel: _llmModel,
      apiKey: _apiKey,
      allowWebSearch: _webSearchEnabled,
    );

    if (response != null) {
      final botResponse = response['response'];
      setState(() {
        _messages.add({"role": "assistant", "content": botResponse});
        if (isVoice) _orbState = OrbState.speaking;
      });

      // Prefer backend TTS for better quality (especially for Sinhala)
      if (isVoice) {
         _speak(botResponse);
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
    showDialog(
      context: context,
      builder: (context) => _SettingsDialog(
        initialName: _assistantName,
        initialLang: _language,
        initialProvider: _llmProvider,
        initialModel: _llmModel,
        initialKey: _apiKey,
        apiService: _apiService, // Pass apiService to handle linking
        onSave: (name, lang, provider, model, key) {
          setState(() {
            _assistantName = name;
            _language = lang;
            _llmProvider = provider;
            _llmModel = model;
            _apiKey = key;
          });
          _updateTtsLanguage();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          // Sidebar (only on Desktop or if needed)
          if (MediaQuery.of(context).size.width > 700)
            Container(
              width: 240,
              decoration: BoxDecoration(
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
                      child: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 400),
                        child: _showChat ? _buildChatView() : _buildOrbView(),
                      ),
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
          
          Row(
            children: [
              if (!_showChat)
                IconButton(
                  icon: const Icon(Icons.chat_bubble_outline, size: 22),
                  onPressed: () => setState(() => _showChat = true),
                ),
              IconButton(
                icon: const Icon(Icons.settings_outlined, size: 22),
                onPressed: _openSettings,
              ),
            ],
          ),
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
                  onTap: () => setState(() => _activeChatId = chat['id']),
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
          const SizedBox(height: 10),
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
            onTap: _handleOrbTap,
            onLongPress: () => setState(() => _showChat = true),
          ),
          const SizedBox(height: 50),
          Text(
            _orbState == OrbState.listening ? "LISTENING..." : 
            _orbState == OrbState.thinking ? "THINKING..." : "NEXUS",
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
    return Container(
      padding: const EdgeInsets.all(30),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _QuickAction(icon: Icons.mail_outline, label: "Gmail", onTap: () {}),
          _QuickAction(icon: Icons.language, label: "Search", onTap: () {}),
          _QuickAction(icon: Icons.note_alt_outlined, label: "Notes", onTap: () {}),
        ],
      ),
    );
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
              return _ChatBubble(message: msg['content'], isUser: isUser);
            },
          ),
        ),
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
          Expanded(
            child: GlassContainer(
              borderRadius: 30,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: TextField(
                controller: _controller,
                onSubmitted: (val) => _sendMessage(val),
                decoration: InputDecoration(
                  hintText: "Message $_assistantName...",
                  hintStyle: TextStyle(color: AppTheme.textDim, fontSize: 14),
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

class _ChatBubble extends StatelessWidget {
  final String message;
  final bool isUser;

  const _ChatBubble({Key? key, required this.message, required this.isUser}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
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

class _SettingsDialog extends StatefulWidget {
  final String initialName;
  final String initialLang;
  final String initialProvider;
  final String initialModel;
  final String initialKey;
  final ApiService apiService;
  final Function(String, String, String, String, String) onSave;

  const _SettingsDialog({
    Key? key,
    required this.initialName,
    required this.initialLang,
    required this.initialProvider,
    required this.initialModel,
    required this.initialKey,
    required this.apiService,
    required this.onSave,
  }) : super(key: key);

  @override
  __SettingsDialogState createState() => __SettingsDialogState();
}

class __SettingsDialogState extends State<_SettingsDialog> {
  late String _name, _lang, _provider, _model, _key;

  @override
  void initState() {
    super.initState();
    _name = widget.initialName;
    _lang = widget.initialLang;
    _provider = widget.initialProvider;
    _model = widget.initialModel;
    _key = widget.initialKey;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text("Settings"),
      backgroundColor: AppTheme.background,
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildField("Assistant Name", _name, (val) => _name = val),
            _buildDropdown("Language", _lang, ["English", "Sinhala", "Tamil"], (val) => setState(() => _lang = val!)),
            _buildDropdown("LLM Provider", _provider, ["openai", "local"], (val) => setState(() => _provider = val!)),
            _buildField("Model Name", _model, (val) => _model = val),
            if (_provider == "openai")
              _buildField("API Key", _key, (val) => _key = val, obscure: true),
            const Divider(height: 20),
            _buildSettingsLink("MANAGE MEMORY", Icons.psychology_outlined, () {
              Navigator.push(context, MaterialPageRoute(builder: (c) => MemoryScreen(apiService: widget.apiService)));
            }),
            _buildSettingsLink("DYNAMIC AUTOMATIONS", Icons.auto_fix_high_outlined, () {
              Navigator.push(context, MaterialPageRoute(builder: (c) => AutomationScreen(apiService: widget.apiService)));
            }),
            const Divider(height: 30),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF25D366), // WhatsApp Green
                foregroundColor: Colors.white,
                minimumSize: const Size(double.infinity, 45),
              ),
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text("LINK NEW DEVICE (P2P)"),
              onPressed: () => _openScanner(context),
            )
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
        ElevatedButton(
          onPressed: () {
            widget.onSave(_name, _lang, _provider, _model, _key);
            Navigator.pop(context);
          },
          child: const Text("Save"),
        ),
      ],
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
              _initWebSocket(); // Refresh WS connection with new token/IP
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Device Linked Successfully!"), backgroundColor: Colors.green),
                );
                Navigator.pop(context);
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
