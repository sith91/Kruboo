import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart'; // Assuming GlassContainer exists

class PluginScreen extends StatefulWidget {
  const PluginScreen({Key? key}) : super(key: key);

  @override
  _PluginScreenState createState() => _PluginScreenState();
}

class _PluginScreenState extends State<PluginScreen> {
  final ApiService _api = ApiService();
  List<dynamic> _plugins = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadPlugins();
  }

  Future<void> _loadPlugins() async {
    setState(() => _isLoading = true);
    final data = await _api.getPlugins();
    // Default plugins if backend returns none
    final fallback = [
      {
        'id': 1,
        'name': 'Gmail',
        'description': 'Email integration',
        'icon_url': null,
        'enabled': false,
      },
      {
        'id': 2,
        'name': 'Search',
        'description': 'Web search capability',
        'icon_url': null,
        'enabled': false,
      },
      {
        'id': 3,
        'name': 'Notes',
        'description': 'Take notes quickly',
        'icon_url': null,
        'enabled': false,
      },
    ];
    final plugins = (data is List && data.isNotEmpty) ? data : fallback;
    setState(() {
      _plugins = plugins;
      _isLoading = false;
    });
  }


  void _togglePlugin(int id, bool enabled) async {
    // Assuming backend endpoint PATCH /plugins/:id with {enabled: bool}
    try {
      await _api.togglePlugin(id, !enabled);
      _loadPlugins();
    } catch (e) {
      debugPrint('Toggle plugin error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text('Plugins', style: GoogleFonts.inter(fontSize: 16)),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.accent))
          : GridView.builder(
              padding: const EdgeInsets.all(16),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 0.9,
              ),
              itemCount: _plugins.length,
              itemBuilder: (context, index) {
                final p = _plugins[index];
                return _PluginCard(
                  id: p['id'],
                  name: p['name'] ?? 'Unnamed',
                  description: p['description'] ?? '',
                  iconUrl: p['icon_url'],
                  enabled: p['enabled'] ?? false,
                  onToggle: _togglePlugin,
                );
              },
            ),
    );
  }
}

class _PluginCard extends StatelessWidget {
  final int id;
  final String name;
  final String description;
  final String? iconUrl;
  final bool enabled;
  final void Function(int id, bool enabled) onToggle;

  const _PluginCard({
    Key? key,
    required this.id,
    required this.name,
    required this.description,
    this.iconUrl,
    required this.enabled,
    required this.onToggle,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Stack(
        children: [
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Colors.white.withOpacity(0.15), Colors.white.withOpacity(0.05)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              border: Border.all(color: Colors.white.withOpacity(0.2), width: 1),
              borderRadius: BorderRadius.circular(16),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: iconUrl != null
                      ? Image.network(iconUrl!, height: 48, width: 48)
                      : const Icon(Icons.extension, size: 48, color: Colors.white70),
                ),
                const SizedBox(height: 8),
                Text(name,
                    style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 4),
                Text(description,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(fontSize: 11, color: Colors.white70)),
                const Spacer(),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(enabled ? 'Enabled' : 'Disabled',
                        style: GoogleFonts.inter(fontSize: 12, color: enabled ? Colors.greenAccent : Colors.redAccent)),
                    Switch(
                      value: enabled,
                      activeColor: AppTheme.accent,
                      onChanged: (_) => onToggle(id, enabled),
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
}
