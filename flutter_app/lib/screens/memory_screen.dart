import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';

class MemoryScreen extends StatefulWidget {
  final ApiService apiService;
  const MemoryScreen({Key? key, required this.apiService}) : super(key: key);

  @override
  _MemoryScreenState createState() => _MemoryScreenState();
}

class _MemoryScreenState extends State<MemoryScreen> {
  List<dynamic> _memories = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMemories();
  }

  Future<void> _loadMemories() async {
    setState(() => _isLoading = true);
    final data = await widget.apiService.getMemories();
    setState(() {
      _memories = data;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text("Assistant Memory", style: GoogleFonts.inter(fontSize: 16)),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator(color: AppTheme.accent))
        : RefreshIndicator(
            onRefresh: _loadMemories,
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _memories.length,
              itemBuilder: (context, index) {
                final m = _memories[index];
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
                            Text(m['fact'], style: GoogleFonts.inter(fontSize: 14, color: AppTheme.text)),
                            const SizedBox(height: 4),
                            Text(m['category'].toUpperCase(), style: GoogleFonts.inter(fontSize: 10, color: AppTheme.accent, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline, color: Colors.redAccent, size: 20),
                        onPressed: () async {
                          await widget.apiService.deleteMemory(m['id']);
                          _loadMemories();
                        },
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
    );
  }
}
