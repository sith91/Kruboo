import 'dart:io';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:file_picker/file_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import '../services/persona_service.dart';
import '../services/llm_config_service.dart';
import '../models/persona.dart';
import 'persona_screen.dart';
import 'memory_screen.dart';
import 'automation_screen.dart';
import 'chat_history_screen.dart';

class SettingsScreen extends StatefulWidget {
  final ApiService apiService;
  final VoidCallback? onSettingsSaved;

  const SettingsScreen({
    Key? key,
    required this.apiService,
    this.onSettingsSaved,
  }) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> with SingleTickerProviderStateMixin {
  int _activeTabIndex = 0;

  // General Settings
  String _assistantName = "Kruuboo";
  bool _voiceActivation = false;
  String _avatarMode = "vrm"; // 'vrm', 'globe', 'pet'
  String _vrmFraming = "bust"; // 'portrait', 'bust', 'full'
  String _visionMode = "cloud"; // 'cloud', 'local'
  bool _privacyMode = false;

  // Identity Settings
  String _feeling = "professional";
  String _activePersonaId = "";
  List<Persona> _personas = [];
  Map<String, dynamic>? _vrmInfo;

  // Language Settings
  String _language = "English";
  String _sttEngine = "local";
  String _ttsLang = "en";

  // Connectivity Settings
  bool _webSearch = true;
  Map<String, dynamic>? _syncStatus;
  Map<String, dynamic> _activeIot = {};
  List<dynamic> _iotConnectors = [];

  // Intelligence Settings
  String _llmProvider = "OpenAI";
  String _llmModel = "gpt-4";
  String _apiKey = "";
  Map<String, dynamic>? _litertStatus;
  bool _isDownloadingLiteRT = false;

  bool _isLoading = true;

  final List<Map<String, dynamic>> _tabs = [
    // Group 0: General
    {"id": "general", "label": "General", "icon": Icons.home_rounded, "group": 0},
    {"id": "identity", "label": "Identity", "icon": Icons.person_rounded, "group": 0},
    {"id": "languages", "label": "Languages", "icon": Icons.language_rounded, "group": 0},
    // Group 1: Connectivity
    {"id": "connections", "label": "Links", "icon": Icons.link_rounded, "group": 1},
    {"id": "devices", "label": "Devices", "icon": Icons.devices_rounded, "group": 1},
    {"id": "iot", "label": "Smart Home", "icon": Icons.home_work_rounded, "group": 1},
    // Group 2: Intelligence
    {"id": "ai", "label": "AI Engine", "icon": Icons.psychology_rounded, "group": 2},
    {"id": "memory", "label": "Memory", "icon": Icons.storage_rounded, "group": 2},
    {"id": "automations", "label": "Automations", "icon": Icons.bolt_rounded, "group": 2},
  ];

  @override
  void initState() {
    super.initState();
    _loadAllSettings();
  }

  Future<void> _loadAllSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final configService = LLMConfigService();
    final config = await configService.loadConfig();
    final personas = await PersonaService().getPersonas();

    setState(() {
      _assistantName = prefs.getString('assistant_name') ?? "Kruuboo";
      _voiceActivation = prefs.getBool('background_listening') ?? false;
      _avatarMode = prefs.getString('avatar_mode') ?? "vrm";
      _vrmFraming = prefs.getString('vrm_display_mode') ?? "bust";
      _visionMode = prefs.getString('object_recognition_mode') ?? "cloud";
      _privacyMode = prefs.getBool('privacy_mode') ?? false;

      _feeling = prefs.getString('feeling') ?? "professional";
      _activePersonaId = prefs.getString('active_persona_id') ?? "";
      _personas = personas;

      _language = prefs.getString('language') ?? "English";
      _sttEngine = prefs.getString('stt_engine') ?? "local";
      _ttsLang = prefs.getString('tts_lang') ?? "en";

      if (config != null) {
        _llmProvider = config.provider;
        _llmModel = config.model;
        _apiKey = config.apiKey;
      }

      _isLoading = false;
    });

    _fetchBackendStatus();
  }

  Future<void> _fetchBackendStatus() async {
    final sync = await widget.apiService.getSyncStatus();
    final litert = await widget.apiService.getLiteRTStatus();
    final vrm = await widget.apiService.getVRMInfo();
    final iot = await widget.apiService.getIoTConnectors();
    final activeIot = await widget.apiService.getIoTActive();

    if (mounted) {
      setState(() {
        _syncStatus = sync;
        _litertStatus = litert;
        _vrmInfo = vrm;
        _iotConnectors = iot;
        _activeIot = activeIot;
      });
    }
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('assistant_name', _assistantName);
    await prefs.setBool('background_listening', _voiceActivation);
    await prefs.setString('avatar_mode', _avatarMode);
    await prefs.setString('vrm_display_mode', _vrmFraming);
    await prefs.setString('object_recognition_mode', _visionMode);
    await prefs.setBool('privacy_mode', _privacyMode);

    await prefs.setString('feeling', _feeling);
    await prefs.setString('active_persona_id', _activePersonaId);

    await prefs.setString('language', _language);
    await prefs.setString('stt_engine', _sttEngine);
    await prefs.setString('tts_lang', _ttsLang);

    final configService = LLMConfigService();
    await configService.saveConfig(LLMConfig(
      provider: _llmProvider,
      model: _llmModel,
      apiKey: _apiKey,
    ));

    if (_activePersonaId.isNotEmpty) {
      await PersonaService().setActivePersona(_activePersonaId);
    }

    widget.onSettingsSaved?.call();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Settings saved successfully"),
          backgroundColor: Color(0xFF6B4CFF),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: AppTheme.background,
        body: Center(
          child: CircularProgressIndicator(color: Color(0xFF6B4CFF)),
        ),
      );
    }

    final isWide = MediaQuery.of(context).size.width > 700;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          children: [
            const Text('⚙️', style: TextStyle(fontSize: 16)),
            const SizedBox(width: 8),
            Text(
              'SETTINGS',
              style: GoogleFonts.inter(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.5,
                color: Colors.white,
              ),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6B4CFF),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              ),
              icon: const Icon(Icons.check, size: 16),
              label: const Text('Save', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              onPressed: _saveSettings,
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(0.5),
          child: Container(color: AppTheme.border, height: 0.5),
        ),
      ),
      body: isWide ? _buildDesktopLayout() : _buildMobileLayout(),
    );
  }

  Widget _buildDesktopLayout() {
    return Row(
      children: [
        Container(
          width: 200,
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            border: Border(right: BorderSide(color: AppTheme.border, width: 0.5)),
          ),
          child: ListView(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
            children: [
              _buildSidebarGroup("GENERAL", 0),
              _buildSidebarGroup("CONNECTIVITY", 1),
              _buildSidebarGroup("INTELLIGENCE", 2),
            ],
          ),
        ),
        Expanded(
          child: Container(
            color: AppTheme.background,
            child: _buildActiveTabContent(),
          ),
        ),
      ],
    );
  }

  Widget _buildMobileLayout() {
    return Column(
      children: [
        // Category switcher bar
        Container(
          height: 48,
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            border: Border(bottom: BorderSide(color: AppTheme.border, width: 0.5)),
          ),
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            itemCount: _tabs.length,
            itemBuilder: (context, index) {
              final tab = _tabs[index];
              final isActive = _activeTabIndex == index;
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: ChoiceChip(
                  label: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(tab['icon'], size: 14, color: isActive ? Colors.white : AppTheme.textDim),
                      const SizedBox(width: 6),
                      Text(tab['label']),
                    ],
                  ),
                  selected: isActive,
                  selectedColor: const Color(0xFF6B4CFF),
                  backgroundColor: AppTheme.surface,
                  labelStyle: TextStyle(
                    fontSize: 12,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
                    color: isActive ? Colors.white : AppTheme.textDim,
                  ),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  onSelected: (selected) {
                    if (selected) setState(() => _activeTabIndex = index);
                  },
                ),
              );
            },
          ),
        ),
        Expanded(
          child: _buildActiveTabContent(),
        ),
      ],
    );
  }

  Widget _buildSidebarGroup(String title, int groupIndex) {
    final groupTabs = _tabs.where((t) => t['group'] == groupIndex).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Text(
            title,
            style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.w700, color: const Color(0xFF64748B), letterSpacing: 1.2),
          ),
        ),
        ...groupTabs.map((tab) {
          final index = _tabs.indexOf(tab);
          final isActive = _activeTabIndex == index;
          return Container(
            margin: const EdgeInsets.symmetric(vertical: 2),
            child: ListTile(
              dense: true,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              tileColor: isActive ? const Color(0xFF6B4CFF).withOpacity(0.25) : Colors.transparent,
              leading: Icon(tab['icon'], size: 16, color: isActive ? const Color(0xFF6B4CFF) : AppTheme.textDim),
              title: Text(
                tab['label'],
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
                  color: isActive ? Colors.white : AppTheme.text,
                ),
              ),
              onTap: () => setState(() => _activeTabIndex = index),
            ),
          );
        }).toList(),
        const SizedBox(height: 8),
      ],
    );
  }

  Widget _buildActiveTabContent() {
    final activeId = _tabs[_activeTabIndex]['id'];

    switch (activeId) {
      case 'general': return _buildGeneralTab();
      case 'identity': return _buildIdentityTab();
      case 'languages': return _buildLanguagesTab();
      case 'connections': return _buildConnectionsTab();
      case 'devices': return _buildDevicesTab();
      case 'iot': return _buildIotTab();
      case 'ai': return _buildAIEngineTab();
      case 'memory': return _buildMemoryTab();
      case 'automations': return _buildAutomationsTab();
      default: return _buildGeneralTab();
    }
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 1. GENERAL TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildGeneralTab() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "VOICE CONTROL",
          child: SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text("Voice Activation (Wake Word)", style: TextStyle(fontSize: 14, color: Colors.white, fontWeight: FontWeight.w500)),
            subtitle: const Text("Listen continuously for trigger phrase in background", style: TextStyle(fontSize: 12, color: AppTheme.textDim)),
            value: _voiceActivation,
            activeColor: const Color(0xFF6B4CFF),
            onChanged: (val) => setState(() => _voiceActivation = val),
          ),
        ),
        _buildSectionCard(
          title: "INTERFACE DISPLAY STYLE",
          child: Column(
            children: [
              _buildRadioOption("3D VRM Anime Character", "vrm", _avatarMode, Icons.face_3_rounded, (val) => setState(() => _avatarMode = val)),
              const Divider(color: AppTheme.border, height: 16),
              _buildRadioOption("Siri Glowing Gradient Orb", "globe", _avatarMode, Icons.blur_on_rounded, (val) => setState(() => _avatarMode = val)),
              const Divider(color: AppTheme.border, height: 16),
              _buildRadioOption("Interactive Pet Avatar", "pet", _avatarMode, Icons.pets_rounded, (val) => setState(() => _avatarMode = val)),
            ],
          ),
        ),
        _buildSectionCard(
          title: "VISUAL INTERPRETER (VISION)",
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildDropdownField(
                label: "Object Recognition Mode",
                value: _visionMode,
                items: const ["cloud", "local"],
                displayNames: const ["Cloud (GPT-4o / Gemini Vision)", "Local Ollama (LLaVA / Llama 3.2 Vision)"],
                onChanged: (val) => setState(() => _visionMode = val),
              ),
            ],
          ),
        ),
        _buildSectionCard(
          title: "PRIVACY & SECURITY",
          child: SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text("Privacy Mode (PII Scrubbing)", style: TextStyle(fontSize: 14, color: Colors.white, fontWeight: FontWeight.w500)),
            subtitle: const Text("Redact names, emails, and phone numbers before sending to cloud APIs", style: TextStyle(fontSize: 12, color: AppTheme.textDim)),
            value: _privacyMode,
            activeColor: const Color(0xFF6B4CFF),
            onChanged: (val) => setState(() => _privacyMode = val),
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 2. IDENTITY TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildIdentityTab() {
    final hasCustomVrm = _vrmInfo?['has_custom'] == true;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "ASSISTANT PROFILE",
          child: Column(
            children: [
              _buildTextField("Assistant Name", _assistantName, (val) => _assistantName = val),
              const SizedBox(height: 14),
              _buildDropdownField(
                label: "Personality Feeling / Tone",
                value: _feeling,
                items: const ["professional", "siri", "friendly", "energetic", "calm", "lethargic", "robotic"],
                displayNames: const [
                  "Professional & Direct",
                  "Siri-like Concise",
                  "Friendly & Enthusiastic",
                  "Energetic & Dynamic",
                  "Calm & Meditative",
                  "Lethargic / Relaxed",
                  "Robotic & Analytical"
                ],
                onChanged: (val) => setState(() => _feeling = val),
              ),
            ],
          ),
        ),
        _buildSectionCard(
          title: "3D VRM AVATAR",
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildDropdownField(
                label: "Camera Framing",
                value: _vrmFraming,
                items: const ["portrait", "bust", "full"],
                displayNames: const ["Head / Portrait", "Upper Body (Bust)", "Full Body"],
                onChanged: (val) => setState(() => _vrmFraming = val),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFF6B4CFF),
                        side: const BorderSide(color: Color(0xFF6B4CFF)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      icon: const Icon(Icons.upload_file_rounded, size: 18),
                      label: const Text("Upload Custom .VRM"),
                      onPressed: () async {
                        final result = await FilePicker.pickFiles(
                          type: FileType.custom,
                          allowedExtensions: ['vrm'],
                        );
                        if (result != null && result.files.single.path != null) {
                          final file = File(result.files.single.path!);
                          final success = await widget.apiService.uploadVRM(file);
                          if (success) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text("VRM avatar uploaded successfully!"), backgroundColor: Colors.green),
                            );
                            _fetchBackendStatus();
                          }
                        }
                      },
                    ),
                  ),
                  if (hasCustomVrm) ...[
                    const SizedBox(width: 10),
                    IconButton(
                      tooltip: "Reset to Default Avatar",
                      icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                      onPressed: () async {
                        await widget.apiService.deleteVRM();
                        _fetchBackendStatus();
                      },
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
        _buildSectionCard(
          title: "VOICE CLONING (ELEVENLABS)",
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.record_voice_over_rounded, color: Color(0xFF6B4CFF)),
            title: const Text("Upload Voice Reference Sample", style: TextStyle(fontSize: 14, color: Colors.white, fontWeight: FontWeight.w500)),
            subtitle: const Text(".mp3 or .wav voice recording for instant cloning", style: TextStyle(fontSize: 12, color: AppTheme.textDim)),
            trailing: const Icon(Icons.chevron_right, color: AppTheme.textDim),
            onTap: () async {
              final result = await FilePicker.pickFiles(
                type: FileType.custom,
                allowedExtensions: ['wav', 'mp3'],
              );
              if (result != null && result.files.single.path != null) {
                final file = File(result.files.single.path!);
                final ok = await widget.apiService.uploadVoice(file);
                if (ok && mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Voice reference uploaded & cloned!"), backgroundColor: Colors.green),
                  );
                }
              }
            },
          ),
        ),
        _buildSectionCard(
          title: "PERSONAS GALLERY",
          child: Column(
            children: [
              if (_personas.isNotEmpty)
                DropdownButtonFormField<String>(
                  value: _activePersonaId.isEmpty ? null : _activePersonaId,
                  decoration: InputDecoration(
                    labelText: "Active Persona",
                    labelStyle: const TextStyle(color: AppTheme.textDim, fontSize: 13),
                    filled: true,
                    fillColor: AppTheme.surface,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  ),
                  dropdownColor: const Color(0xFF1E293B),
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                  hint: const Text("None (Standard Assistant)", style: TextStyle(color: AppTheme.textDim)),
                  items: [
                    const DropdownMenuItem<String>(value: '', child: Text("None (Standard Assistant)")),
                    ..._personas.map((p) => DropdownMenuItem<String>(value: p.id, child: Text(p.name))),
                  ],
                  onChanged: (val) => setState(() => _activePersonaId = val ?? ''),
                ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: AppTheme.border),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  icon: const Icon(Icons.people_outline, size: 16),
                  label: const Text("Manage Personas"),
                  onPressed: () {
                    Navigator.push(context, MaterialPageRoute(builder: (_) => const PersonaScreen()))
                        .then((_) => _loadAllSettings());
                  },
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 3. LANGUAGES TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildLanguagesTab() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "APP & ASSISTANT LANGUAGE",
          child: _buildDropdownField(
            label: "Primary Language",
            value: _language,
            items: const ["English", "Sinhala", "Tamil"],
            onChanged: (val) => setState(() => _language = val),
          ),
        ),
        _buildSectionCard(
          title: "VOICE INPUT (SPEECH-TO-TEXT)",
          child: Column(
            children: [
              _buildDropdownField(
                label: "STT Engine",
                value: _sttEngine,
                items: const ["local", "whisper"],
                displayNames: const ["Local Vosk (Offline)", "OpenAI Whisper (Cloud)"],
                onChanged: (val) => setState(() => _sttEngine = val),
              ),
            ],
          ),
        ),
        _buildSectionCard(
          title: "VOICE OUTPUT (TEXT-TO-SPEECH)",
          child: Column(
            children: [
              _buildDropdownField(
                label: "TTS Locale Code",
                value: _ttsLang,
                items: const ["en", "si", "ta"],
                displayNames: const ["English (en-US)", "Sinhala (si-LK)", "Tamil (ta-IN)"],
                onChanged: (val) => setState(() => _ttsLang = val),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 4. LINKS (CONNECTORS) TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildConnectionsTab() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "GOOGLE WORKSPACE CONNECTORS",
          child: Column(
            children: [
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.mail_outline_rounded, color: Colors.redAccent),
                title: const Text("Gmail Integration", style: TextStyle(color: Colors.white, fontSize: 14)),
                subtitle: const Text("Read unread emails and draft responses", style: TextStyle(color: AppTheme.textDim, fontSize: 12)),
                trailing: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1E293B)),
                  child: const Text("Authorize", style: TextStyle(fontSize: 12, color: Colors.white)),
                  onPressed: () async {
                    final res = await widget.apiService.authGmail();
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(res?['message'] ?? "Gmail authorization requested.")),
                      );
                    }
                  },
                ),
              ),
              const Divider(color: AppTheme.border),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.calendar_today_rounded, color: Colors.blueAccent),
                title: const Text("Google Calendar", style: TextStyle(color: Colors.white, fontSize: 14)),
                subtitle: const Text("Schedule and query calendar meetings", style: TextStyle(color: AppTheme.textDim, fontSize: 12)),
                trailing: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1E293B)),
                  child: const Text("Authorize", style: TextStyle(fontSize: 12, color: Colors.white)),
                  onPressed: () async {
                    final res = await widget.apiService.authCalendar();
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(res?['message'] ?? "Calendar authorization requested.")),
                      );
                    }
                  },
                ),
              ),
            ],
          ),
        ),
        _buildSectionCard(
          title: "AUTONOMOUS WEB RESEARCH",
          child: SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text("Live Internet Search", style: TextStyle(color: Colors.white, fontSize: 14)),
            subtitle: const Text("Allow assistant to search DuckDuckGo / Trafilatura for real-time answers", style: TextStyle(color: AppTheme.textDim, fontSize: 12)),
            value: _webSearch,
            activeColor: const Color(0xFF6B4CFF),
            onChanged: (val) => setState(() => _webSearch = val),
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 5. DEVICES TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildDevicesTab() {
    final ip = _syncStatus?['local_ip'] ?? "Unknown";

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "LOCAL NETWORK SYNCHRONIZATION",
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.wifi_tethering_rounded, color: Color(0xFF00F2FE), size: 20),
                  const SizedBox(width: 8),
                  Text("Backend Host IP: $ip", style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                ],
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6B4CFF),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  icon: const Icon(Icons.qr_code_scanner_rounded),
                  label: const Text("Scan Desktop QR Code to Pair"),
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => Scaffold(
                          appBar: AppBar(title: const Text("Scan Pairing QR")),
                          body: MobileScanner(
                            onDetect: (capture) {
                              final barcodes = capture.barcodes;
                              for (final barcode in barcodes) {
                                if (barcode.rawValue != null) {
                                  try {
                                    // IP:Port|Token or JSON
                                    final val = barcode.rawValue!;
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text("Linked to $val")),
                                    );
                                  } catch (_) {}
                                }
                              }
                            },
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 6. SMART HOME (IOT) TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildIotTab() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "CONNECTOR GALLERY",
          child: Column(
            children: [
              _buildIoTItem("tasmota", "Tasmota / Sonoff", "Local smart plugs & relays", Icons.power_rounded),
              const Divider(color: AppTheme.border),
              _buildIoTItem("wled", "WLED Addressable Lights", "ESP32 LED strip controllers", Icons.lightbulb_outline),
              const Divider(color: AppTheme.border),
              _buildIoTItem("philips_hue", "Philips Hue Bridge", "Zigbee lighting bridge", Icons.hub_outlined),
              const Divider(color: AppTheme.border),
              _buildIoTItem("tuya", "Tuya / Smart Life", "Cloud smart devices", Icons.cloud_outlined),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildIoTItem(String id, String name, String subtitle, IconData icon) {
    final isConfigured = _activeIot.containsKey(id);

    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: isConfigured ? const Color(0xFF00FF87) : const Color(0xFF6B4CFF)),
      title: Text(name, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
      subtitle: Text(subtitle, style: const TextStyle(color: AppTheme.textDim, fontSize: 12)),
      trailing: ElevatedButton(
        style: ElevatedButton.styleFrom(
          backgroundColor: isConfigured ? const Color(0xFF00FF87).withOpacity(0.2) : const Color(0xFF1E293B),
          foregroundColor: isConfigured ? const Color(0xFF00FF87) : Colors.white,
        ),
        child: Text(isConfigured ? "Connected" : "Configure", style: const TextStyle(fontSize: 12)),
        onPressed: () {
          _showIoTConfigDialog(id, name);
        },
      ),
    );
  }

  void _showIoTConfigDialog(String vendorId, String vendorName) {
    final ipController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: Text("Configure $vendorName", style: const TextStyle(color: Colors.white, fontSize: 16)),
        content: TextField(
          controller: ipController,
          style: const TextStyle(color: Colors.white),
          decoration: const InputDecoration(
            labelText: "Device IP or Bridge Address",
            labelStyle: TextStyle(color: AppTheme.textDim),
          ),
        ),
        actions: [
          TextButton(
            child: const Text("Cancel"),
            onPressed: () => Navigator.pop(ctx),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6B4CFF)),
            child: const Text("Save & Connect"),
            onPressed: () async {
              await widget.apiService.activateIoTConnector(vendorId, {"ip_address": ipController.text.trim()});
              Navigator.pop(ctx);
              _fetchBackendStatus();
            },
          ),
        ],
      ),
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 7. AI ENGINE TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildAIEngineTab() {
    final isModelDownloaded = _litertStatus?['litert_model_downloaded'] == true;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "LARGE LANGUAGE MODEL ROUTING",
          child: Column(
            children: [
              _buildDropdownField(
                label: "LLM Provider",
                value: _llmProvider,
                items: const ["OpenAI", "Claude", "Deepseek", "Gemini", "Grok", "Local"],
                onChanged: (val) => setState(() => _llmProvider = val),
              ),
              const SizedBox(height: 14),
              _buildTextField("Model Name / ID", _llmModel, (val) => _llmModel = val),
              const SizedBox(height: 14),
              _buildTextField("API Key", _apiKey, (val) => _apiKey = val, obscure: true),
            ],
          ),
        ),
        _buildSectionCard(
          title: "ON-DEVICE LITERT-LM / GEMMA 4",
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    isModelDownloaded ? Icons.check_circle_rounded : Icons.info_outline_rounded,
                    color: isModelDownloaded ? const Color(0xFF00FF87) : const Color(0xFFFFB800),
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    isModelDownloaded ? "Gemma 4 E2B Downloaded & Ready" : "Gemma 4 E2B Not Downloaded",
                    style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (!isModelDownloaded)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF6B4CFF),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: _isDownloadingLiteRT
                        ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.download_rounded, size: 16),
                    label: Text(_isDownloadingLiteRT ? "Downloading in Background..." : "Download Gemma 4 E2B Model"),
                    onPressed: _isDownloadingLiteRT ? null : () async {
                      setState(() => _isDownloadingLiteRT = true);
                      await widget.apiService.downloadLiteRTModel();
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text("LiteRT-LM Gemma 4 E2B download started.")),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 8. MEMORY TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildMemoryTab() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "PERSONAL FACTS MEMORY",
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.storage_rounded, color: Color(0xFF6B4CFF)),
            title: const Text("Manage SQLite Facts", style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
            subtitle: const Text("View, edit, or delete facts stored by the model", style: TextStyle(color: AppTheme.textDim, fontSize: 12)),
            trailing: const Icon(Icons.chevron_right, color: AppTheme.textDim),
            onTap: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => MemoryScreen(apiService: widget.apiService)));
            },
          ),
        ),
        _buildSectionCard(
          title: "CHAT SESSIONS & TRANSCRIPTS",
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.history_rounded, color: Color(0xFF6B4CFF)),
            title: const Text("Chat History", style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
            subtitle: const Text("Review previous conversations and session logs", style: TextStyle(color: AppTheme.textDim, fontSize: 12)),
            trailing: const Icon(Icons.chevron_right, color: AppTheme.textDim),
            onTap: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => ChatHistoryScreen(apiService: widget.apiService)));
            },
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 9. AUTOMATIONS TAB
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildAutomationsTab() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildSectionCard(
          title: "BACKGROUND AUTOMATIONS ENGINE",
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.bolt_rounded, color: Color(0xFF6B4CFF)),
            title: const Text("Rule-Based Automation Engine", style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
            subtitle: const Text("Triggers: Time, Battery, Weather, Stock, Email -> Actions: Apps, Media, Voice Alerts", style: TextStyle(color: AppTheme.textDim, fontSize: 12)),
            trailing: const Icon(Icons.chevron_right, color: AppTheme.textDim),
            onTap: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => AutomationScreen(apiService: widget.apiService)));
            },
          ),
        ),
      ],
    );
  }

  // ═════════════════════════════════════════════════════════════════════════
  // REUSABLE UI BUILDERS
  // ═════════════════════════════════════════════════════════════════════════
  Widget _buildSectionCard({required String title, required Widget child}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.border, width: 0.8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.3,
              color: const Color(0xFF6B4CFF),
            ),
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }

  Widget _buildTextField(String label, String initialValue, Function(String) onChanged, {bool obscure = false}) {
    return TextFormField(
      initialValue: initialValue,
      obscureText: obscure,
      style: const TextStyle(color: Colors.white, fontSize: 13),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: AppTheme.textDim, fontSize: 12),
        filled: true,
        fillColor: AppTheme.surface,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      ),
      onChanged: onChanged,
    );
  }

  Widget _buildDropdownField({
    required String label,
    required String value,
    required List<String> items,
    List<String>? displayNames,
    required Function(String) onChanged,
  }) {
    final validItems = items.contains(value) ? items : [value, ...items];

    return DropdownButtonFormField<String>(
      value: value,
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: AppTheme.textDim, fontSize: 12),
        filled: true,
        fillColor: AppTheme.surface,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      ),
      dropdownColor: const Color(0xFF1E293B),
      style: const TextStyle(color: Colors.white, fontSize: 13),
      items: validItems.map((it) {
        final index = items.indexOf(it);
        final title = (displayNames != null && index >= 0 && index < displayNames.length) ? displayNames[index] : it;
        return DropdownMenuItem<String>(value: it, child: Text(title));
      }).toList(),
      onChanged: (val) {
        if (val != null) onChanged(val);
      },
    );
  }

  Widget _buildRadioOption(String label, String value, String groupValue, IconData icon, Function(String) onSelect) {
    final isSelected = value == groupValue;
    return InkWell(
      onTap: () => onSelect(value),
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
        child: Row(
          children: [
            Icon(icon, size: 18, color: isSelected ? const Color(0xFF6B4CFF) : AppTheme.textDim),
            const SizedBox(width: 10),
            Expanded(
              child: Text(label, style: TextStyle(fontSize: 13, color: isSelected ? Colors.white : AppTheme.textDim, fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400)),
            ),
            if (isSelected)
              const Icon(Icons.check_circle_rounded, color: Color(0xFF6B4CFF), size: 18)
            else
              const Icon(Icons.radio_button_unchecked_rounded, color: AppTheme.textDim, size: 18),
          ],
        ),
      ),
    );
  }
}
