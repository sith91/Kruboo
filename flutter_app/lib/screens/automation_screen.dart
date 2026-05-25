import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';

class AutomationScreen extends StatefulWidget {
  final ApiService apiService;
  const AutomationScreen({Key? key, required this.apiService}) : super(key: key);

  @override
  _AutomationScreenState createState() => _AutomationScreenState();
}

class _AutomationScreenState extends State<AutomationScreen> {
  List<dynamic> _automations = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadAutomations();
  }

  Future<void> _loadAutomations() async {
    setState(() => _isLoading = true);
    final data = await widget.apiService.getAutomations();
    setState(() {
      _automations = data;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text("Automations", style: GoogleFonts.inter(fontSize: 16)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.add_circle_outline, color: AppTheme.accent),
            onPressed: () => _showAddDialog(),
          )
        ],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator(color: AppTheme.accent))
        : ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _automations.length,
            itemBuilder: (context, index) {
              final a = _automations[index];
              return Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.border, width: 0.5),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(a['name'], style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.text)),
                          const SizedBox(height: 4),
                          Text("${a['trigger_type'].toUpperCase()} ➔ ${a['action_type'].toUpperCase()}", 
                               style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textDim)),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.redAccent, size: 20),
                      onPressed: () async {
                        await widget.apiService.deleteAutomation(a['id']);
                        _loadAutomations();
                      },
                    ),
                  ],
                ),
              );
            },
          ),
    );
  }

  void _showAddDialog() {
    // Simple placeholder for adding - in a real app this would be a full form
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Create Automation"),
        content: const Text("Automation configuration is synced with your desktop. Please use the Desktop app for complex rule creation."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("OK"))
        ],
      ),
    );
  }
}
