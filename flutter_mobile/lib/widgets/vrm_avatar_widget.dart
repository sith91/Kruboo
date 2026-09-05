import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

class VRMAvatarWidget extends StatefulWidget {
  final bool isSpeaking;
  final String emotion; // 'neutral', 'happy', 'surprised', 'thinking', 'angry', 'sad'
  final String feeling; // 'professional', 'energetic', 'lethargic'
  final double lipSyncVolume;
  final String framing; // 'portrait', 'bust', 'full'
  final VoidCallback? onTap;
  final Function(bool isReady)? onReady;

  const VRMAvatarWidget({
    Key? key,
    this.isSpeaking = false,
    this.emotion = 'neutral',
    this.feeling = 'professional',
    this.lipSyncVolume = 0.0,
    this.framing = 'portrait',
    this.onTap,
    this.onReady,
  }) : super(key: key);

  @override
  State<VRMAvatarWidget> createState() => _VRMAvatarWidgetState();
}

class _VRMAvatarWidgetState extends State<VRMAvatarWidget> {
  late final WebViewController _controller;
  bool _isEngineReady = false;

  @override
  void initState() {
    super.initState();
    _initWebView();
  }

  void _initWebView() {
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.transparent)
      ..addJavaScriptChannel(
        'FlutterVRMChannel',
        onMessageReceived: (JavaScriptMessage message) {
          try {
            final data = jsonDecode(message.message);
            if (data['type'] == 'ready') {
              setState(() {
                _isEngineReady = true;
              });
              _syncAllProperties();
              widget.onReady?.call(true);
            }
          } catch (e) {
            debugPrint("VRM Channel parse error: $e");
          }
        },
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (String url) {
            debugPrint("VRM 3D Engine Page Loaded: $url");
          },
          onWebResourceError: (WebResourceError error) {
            debugPrint("VRM WebResourceError: ${error.description}");
          },
        ),
      )
      ..loadFlutterAsset('assets/vrm/index.html');
  }

  @override
  void didUpdateWidget(covariant VRMAvatarWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_isEngineReady) return;

    if (oldWidget.isSpeaking != widget.isSpeaking) {
      _controller.runJavaScript("if (window.flutterVRM) window.flutterVRM.setSpeaking(${widget.isSpeaking});");
    }
    if (oldWidget.lipSyncVolume != widget.lipSyncVolume) {
      _controller.runJavaScript("if (window.flutterVRM) window.flutterVRM.setLipSyncVolume(${widget.lipSyncVolume});");
    }
    if (oldWidget.emotion != widget.emotion) {
      _controller.runJavaScript("if (window.flutterVRM) window.flutterVRM.setExpression('${widget.emotion}');");
    }
    if (oldWidget.feeling != widget.feeling) {
      _controller.runJavaScript("if (window.flutterVRM) window.flutterVRM.setFeeling('${widget.feeling}');");
    }
    if (oldWidget.framing != widget.framing) {
      _controller.runJavaScript("if (window.flutterVRM) window.flutterVRM.setCameraFraming('${widget.framing}');");
    }
  }

  void _syncAllProperties() {
    _controller.runJavaScript("""
      if (window.flutterVRM) {
        window.flutterVRM.setSpeaking(${widget.isSpeaking});
        window.flutterVRM.setLipSyncVolume(${widget.lipSyncVolume});
        window.flutterVRM.setExpression('${widget.emotion}');
        window.flutterVRM.setFeeling('${widget.feeling}');
        window.flutterVRM.setCameraFraming('${widget.framing}');
      }
    """);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      behavior: HitTestBehavior.opaque,
      child: Stack(
        alignment: Alignment.center,
        children: [
          WebViewWidget(controller: _controller),
          if (!_isEngineReady)
            const SizedBox(
              width: 32,
              height: 32,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF00F2FE)),
              ),
            ),
        ],
      ),
    );
  }
}
