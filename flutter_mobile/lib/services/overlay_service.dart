import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';

class OverlayService {
  static final OverlayService _instance = OverlayService._internal();
  factory OverlayService() => _instance;
  OverlayService._internal();

  bool _isOverlayActive = false;
  bool get isOverlayActive => _isOverlayActive;

  /// Check whether the SYSTEM_ALERT_WINDOW permission is granted
  Future<bool> checkPermission() async {
    try {
      final bool granted = await FlutterOverlayWindow.isPermissionGranted();
      return granted;
    } catch (e) {
      debugPrint("Error checking overlay permission: $e");
      return false;
    }
  }

  /// Request SYSTEM_ALERT_WINDOW permission
  Future<bool> requestPermission() async {
    try {
      final bool? granted = await FlutterOverlayWindow.requestPermission();
      return granted ?? false;
    } catch (e) {
      debugPrint("Error requesting overlay permission: $e");
      return false;
    }
  }

  /// Launch the floating overlay assistant
  Future<bool> showFloatingOverlay({
    int width = 240,
    int height = 240,
    bool enableDrag = true,
  }) async {
    try {
      final bool hasPermission = await checkPermission();
      if (!hasPermission) {
        final bool granted = await requestPermission();
        if (!granted) return false;
      }

      await FlutterOverlayWindow.showOverlay(
        enableDrag: enableDrag,
        overlayTitle: "Kruuboo Floating Assistant",
        overlayContent: "Kruuboo is running in the background",
        flag: OverlayFlag.defaultFlag,
        visibility: NotificationVisibility.visibilityPublic,
        positionGravity: PositionGravity.auto,
        height: height,
        width: width,
      );

      _isOverlayActive = true;
      return true;
    } catch (e) {
      debugPrint("Error showing overlay window: $e");
      return false;
    }
  }

  /// Close the floating overlay
  Future<void> closeOverlay() async {
    try {
      await FlutterOverlayWindow.closeOverlay();
      _isOverlayActive = false;
    } catch (e) {
      debugPrint("Error closing overlay window: $e");
    }
  }

  /// Send message or trigger to the overlay window
  Future<void> shareDataToOverlay(dynamic data) async {
    try {
      await FlutterOverlayWindow.shareData(data);
    } catch (e) {
      debugPrint("Error sending data to overlay: $e");
    }
  }
}
