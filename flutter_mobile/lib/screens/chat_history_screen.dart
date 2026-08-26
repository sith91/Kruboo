import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class ChatHistoryScreen extends StatefulWidget {
  final ApiService apiService;

  const ChatHistoryScreen({Key? key, required this.apiService})
      : super(key: key);

  @override
  _ChatHistoryScreenState createState() => _ChatHistoryScreenState();
}

class _ChatHistoryScreenState extends State<ChatHistoryScreen> {
  List<dynamic> _sessions = [];
  bool _loading = true;
  String? _errorMsg;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    setState(() {
      _loading = true;
      _errorMsg = null;
    });
    final sessions = await widget.apiService.getChatSessions();
    if (mounted) {
      setState(() {
        _sessions = sessions;
        _loading = false;
      });
    }
  }

  Future<void> _deleteSession(String chatId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF1C1C1E),
        title: Text('Delete Conversation',
            style: GoogleFonts.inter(color: AppTheme.text)),
        content: Text(
          'This conversation will be permanently deleted.',
          style: GoogleFonts.inter(color: AppTheme.textDim, fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await widget.apiService.deleteChat(chatId);
      _loadSessions();
    }
  }

  void _openSession(Map<String, dynamic> session) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _ChatDetailScreen(
          apiService: widget.apiService,
          session: session,
        ),
      ),
    );
  }

  String _formatDate(String? isoStr) {
    if (isoStr == null) return '';
    try {
      final dt = DateTime.parse(isoStr).toLocal();
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inDays == 0) {
        final h = dt.hour.toString().padLeft(2, '0');
        final m = dt.minute.toString().padLeft(2, '0');
        return 'Today $h:$m';
      } else if (diff.inDays == 1) {
        return 'Yesterday';
      } else if (diff.inDays < 7) {
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        return days[dt.weekday - 1];
      } else {
        return '${dt.day}/${dt.month}/${dt.year}';
      }
    } catch (_) {
      return isoStr;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        centerTitle: true,
        title: Text(
          'CHAT HISTORY',
          style: GoogleFonts.inter(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            letterSpacing: 2,
            color: AppTheme.textDim,
          ),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: _loadSessions,
            tooltip: 'Refresh',
          ),
        ],
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(0.5),
          child: Container(height: 0.5, color: AppTheme.border),
        ),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.accent))
          : _errorMsg != null
              ? Center(
                  child: Text(_errorMsg!,
                      style: const TextStyle(color: AppTheme.textDim)))
              : _sessions.isEmpty
                  ? _buildEmpty()
                  : RefreshIndicator(
                      onRefresh: _loadSessions,
                      color: AppTheme.accent,
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        itemCount: _sessions.length,
                        itemBuilder: (ctx, i) =>
                            _buildSessionTile(_sessions[i]),
                      ),
                    ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.chat_bubble_outline_rounded,
              size: 56, color: AppTheme.textDim.withOpacity(0.4)),
          const SizedBox(height: 16),
          Text('No conversations yet',
              style: GoogleFonts.inter(
                  color: AppTheme.textDim,
                  fontSize: 15,
                  fontWeight: FontWeight.w500)),
          const SizedBox(height: 6),
          Text('Your past chats will appear here.',
              style: GoogleFonts.inter(color: AppTheme.textDim, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildSessionTile(dynamic session) {
    final chatId = session['chat_id'] as String;
    final firstMsg = session['first_message'] as String? ?? '';
    final msgCount = session['message_count'] as int? ?? 0;
    final lastAt = _formatDate(session['last_at'] as String?);

    return Dismissible(
      key: Key(chatId),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: AppTheme.error.withOpacity(0.15),
          borderRadius: BorderRadius.circular(14),
        ),
        child: const Icon(Icons.delete_outline_rounded,
            color: AppTheme.error, size: 22),
      ),
      confirmDismiss: (_) async {
        await _deleteSession(chatId);
        return false; // _loadSessions will rebuild the list
      },
      child: GestureDetector(
        onTap: () => _openSession(session),
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.border, width: 0.5),
          ),
          child: Row(
            children: [
              // Avatar / icon
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: AppTheme.accent.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.chat_bubble_outline_rounded,
                    color: AppTheme.accent, size: 20),
              ),
              const SizedBox(width: 14),
              // Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      firstMsg.length > 60
                          ? '${firstMsg.substring(0, 60)}…'
                          : firstMsg,
                      style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: AppTheme.text),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text('$msgCount messages',
                            style: GoogleFonts.inter(
                                fontSize: 11, color: AppTheme.textDim)),
                        const SizedBox(width: 8),
                        Container(
                            width: 3,
                            height: 3,
                            decoration: const BoxDecoration(
                                color: AppTheme.textDim,
                                shape: BoxShape.circle)),
                        const SizedBox(width: 8),
                        Text(lastAt,
                            style: GoogleFonts.inter(
                                fontSize: 11, color: AppTheme.textDim)),
                      ],
                    ),
                  ],
                ),
              ),
              // Delete button
              IconButton(
                icon: const Icon(Icons.delete_outline_rounded,
                    color: AppTheme.textDim, size: 18),
                onPressed: () => _deleteSession(chatId),
                tooltip: 'Delete',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Chat Detail Screen ─────────────────────────────────────────────────────

class _ChatDetailScreen extends StatefulWidget {
  final ApiService apiService;
  final Map<String, dynamic> session;

  const _ChatDetailScreen(
      {Key? key, required this.apiService, required this.session})
      : super(key: key);

  @override
  __ChatDetailScreenState createState() => __ChatDetailScreenState();
}

class __ChatDetailScreenState extends State<_ChatDetailScreen> {
  List<dynamic> _messages = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadMessages();
  }

  Future<void> _loadMessages() async {
    final msgs = await widget.apiService
        .getChatMessages(widget.session['chat_id'] as String);
    if (mounted) {
      setState(() {
        _messages = msgs;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final firstMsg = widget.session['first_message'] as String? ?? 'Conversation';
    final title = firstMsg.length > 30
        ? '${firstMsg.substring(0, 30)}…'
        : firstMsg;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        centerTitle: true,
        title: Text(
          title,
          style: GoogleFonts.inter(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.textDim),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(0.5),
          child: Container(height: 0.5, color: AppTheme.border),
        ),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.accent))
          : _messages.isEmpty
              ? Center(
                  child: Text('No messages',
                      style: GoogleFonts.inter(color: AppTheme.textDim)))
              : ListView.builder(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  itemCount: _messages.length,
                  itemBuilder: (_, i) => _buildBubble(_messages[i]),
                ),
    );
  }

  Widget _buildBubble(dynamic msg) {
    final isUser = (msg['role'] as String?) == 'user';
    final content = msg['content'] as String? ?? '';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isUser
              ? AppTheme.accent.withOpacity(0.15)
              : AppTheme.surface,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          border: Border.all(
            color: isUser
                ? AppTheme.accent.withOpacity(0.3)
                : AppTheme.border,
            width: 0.5,
          ),
        ),
        child: Text(
          content,
          style: GoogleFonts.inter(
              fontSize: 14, color: AppTheme.text, height: 1.5),
        ),
      ),
    );
  }
}
