import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

enum OrbState { idle, listening, thinking, speaking }

class OrbWidget extends StatefulWidget {
  final OrbState state;
  final ApiService? apiService;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;

  const OrbWidget({
    Key? key,
    required this.state,
    this.apiService,
    required this.onTap,
    this.onLongPress,
  }) : super(key: key);

  @override
  _OrbWidgetState createState() => _OrbWidgetState();
}

class _OrbWidgetState extends State<OrbWidget> with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _rotationController;
  late AnimationController _auraController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();

    _auraController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _rotationController.dispose();
    _auraController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    bool isListening = widget.state == OrbState.listening;
    bool isThinking = widget.state == OrbState.thinking;

    return GestureDetector(
      onTap: widget.onTap,
      onLongPress: widget.onLongPress,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Aura Rings (only when listening)
          if (isListening)
            ...List.generate(3, (index) {
              return AnimatedBuilder(
                animation: _auraController,
                builder: (context, child) {
                  double progress = (_auraController.value + (index * 0.33)) % 1.0;
                  return Container(
                    width: 70 + (progress * 160),
                    height: 70 + (progress * 160),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: AppTheme.accent.withOpacity((1 - progress) * 0.4),
                        width: 1.5,
                      ),
                    ),
                  );
                },
              );
            }),

          // Background Glow
          AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              double scale = 1.0 + (_pulseController.value * (isListening ? 0.3 : 0.1));
              return Container(
                width: 120 * scale,
                height: 120 * scale,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: (isListening ? Colors.pinkAccent : AppTheme.accent).withOpacity(0.4),
                      blurRadius: 40 * scale,
                      spreadRadius: 10 * scale,
                    )
                  ],
                ),
              );
            },
          ),

          // Main Orb / Custom Character
          AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              double scale = 1.0 + (_pulseController.value * (isListening || isThinking ? 0.15 : 0.05));
              return Transform.scale(
                scale: scale,
                child: widget.apiService != null
                    ? Image.network(
                        '${widget.apiService!.baseUrl}/pet/${widget.state.name}',
                        width: 100,
                        height: 100,
                        fit: BoxFit.contain,
                        gaplessPlayback: true,
                        errorBuilder: (context, error, stackTrace) {
                          return _buildClassicGlobe(isListening, isThinking);
                        },
                      )
                    : _buildClassicGlobe(isListening, isThinking),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildClassicGlobe(bool isListening, bool isThinking) {
    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white24, width: 0.5),
        gradient: RadialGradient(
          center: const Alignment(-0.3, -0.4),
          colors: isListening
              ? [const Color(0xFFFDA4AF), const Color(0xFFF43F5E), const Color(0xFF9F1239)]
              : [const Color(0xFFC4B5FD), const Color(0xFF7C3AED), const Color(0xFF4C1D95)],
        ),
      ),
      child: Stack(
        children: [
          // Glossy Sheen
          Positioned(
            top: 10,
            left: 15,
            child: Container(
              width: 30,
              height: 20,
              decoration: const BoxDecoration(
                shape: BoxShape.rectangle,
                borderRadius: BorderRadius.all(Radius.elliptical(30, 20)),
                gradient: RadialGradient(
                  colors: [Colors.white54, Colors.transparent],
                ),
              ),
            ),
          ),
          
          // Waveform bars (if listening)
          if (isListening)
            Center(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  return _WaveBar(
                    index: index,
                    baseHeight: 8 + (index % 3 * 6.0),
                  );
                }),
              ),
            ),
        ],
      ),
    );
  }
}

class _WaveBar extends StatefulWidget {
  final int index;
  final double baseHeight;

  const _WaveBar({Key? key, required this.index, required this.baseHeight}) : super(key: key);

  @override
  __WaveBarState createState() => __WaveBarState();
}

class __WaveBarState extends State<_WaveBar> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: 400 + (widget.index * 100)),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 2),
          width: 3,
          height: widget.baseHeight + (_controller.value * 12),
          decoration: BoxDecoration(
            color: Colors.white70,
            borderRadius: BorderRadius.circular(2),
          ),
        );
      },
    );
  }
}
