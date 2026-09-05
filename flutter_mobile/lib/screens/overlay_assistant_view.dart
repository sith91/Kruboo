import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';
import '../widgets/vrm_avatar_widget.dart';
import '../widgets/orb_widget.dart';

class OverlayAssistantView extends StatefulWidget {
  const OverlayAssistantView({Key? key}) : super(key: key);

  @override
  State<OverlayAssistantView> createState() => _OverlayAssistantViewState();
}

class _OverlayAssistantViewState extends State<OverlayAssistantView> {
  String _mode = 'vrm'; // 'vrm' or 'orb'
  String _status = 'idle'; // 'idle', 'listening', 'thinking', 'speaking'
  bool _isSpeaking = false;
  String _emotion = 'neutral';
  String _feeling = 'professional';

  @override
  void initState() {
    super.initState();
    FlutterOverlayWindow.overlayListener.listen((event) {
      if (event != null) {
        try {
          final data = event is Map ? event : jsonDecode(event.toString());
          if (data['status'] != null) {
            setState(() {
              _status = data['status'];
              _isSpeaking = _status == 'speaking';
              if (data['emotion'] != null) _emotion = data['emotion'];
              if (data['feeling'] != null) _feeling = data['feeling'];
              if (data['mode'] != null) _mode = data['mode'];
            });
          }
        } catch (e) {
          debugPrint("Overlay event decode error: $e");
        }
      }
    });
  }

  void _onTapAssistant() async {
    // Notify main app to trigger voice listening
    await FlutterOverlayWindow.shareData(jsonEncode({
      'action': 'voice_trigger'
    }));
  }

  void _onClose() async {
    await FlutterOverlayWindow.closeOverlay();
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Center(
        child: Container(
          width: 170,
          height: 170,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                const Color(0xFF1E293B).withOpacity(0.85),
                const Color(0xFF0F172A).withOpacity(0.95),
              ],
            ),
            boxShadow: [
              BoxShadow(
                color: _status == 'listening'
                    ? const Color(0xFF00F2FE).withOpacity(0.7)
                    : _status == 'speaking'
                        ? const Color(0xFFFF007F).withOpacity(0.6)
                        : Colors.black.withOpacity(0.4),
                blurRadius: 20,
                spreadRadius: 2,
              ),
            ],
            border: Border.all(
              color: Colors.white.withOpacity(0.2),
              width: 1.5,
            ),
          ),
          child: Stack(
            alignment: Alignment.center,
            children: [
              if (_mode == 'vrm')
                ClipOval(
                  child: SizedBox(
                    width: 160,
                    height: 160,
                    child: VRMAvatarWidget(
                      isSpeaking: _isSpeaking,
                      emotion: _emotion,
                      feeling: _feeling,
                      framing: 'portrait',
                      onTap: _onTapAssistant,
                    ),
                  ),
                )
              else
                OrbWidget(
                  state: _status == 'listening'
                      ? OrbState.listening
                      : _status == 'thinking'
                          ? OrbState.thinking
                          : OrbState.idle,
                  onTap: _onTapAssistant,
                ),

              // Dismiss X button
              Positioned(
                top: 4,
                right: 4,
                child: GestureDetector(
                  onTap: _onClose,
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.black.withOpacity(0.6),
                      border: Border.all(color: Colors.white24, width: 1),
                    ),
                    child: const Icon(
                      Icons.close,
                      color: Colors.white70,
                      size: 14,
                    ),
                  ),
                ),
              ),

              // Status indicator chip
              if (_status != 'idle')
                Positioned(
                  bottom: 6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.75),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: _status == 'listening'
                            ? const Color(0xFF00F2FE)
                            : const Color(0xFFFF0844),
                        width: 1,
                      ),
                    ),
                    child: Text(
                      _status.toUpperCase(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
