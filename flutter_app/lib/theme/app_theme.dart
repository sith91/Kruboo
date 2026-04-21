import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color background = Color(0xFF0C0C0E);
  static const Color surface = Color(0x0FFFFFFF);
  static const Color surfaceHover = Color(0x17FFFFFF);
  static const Color border = Color(0x17FFFFFF);
  static const Color accent = Color(0xFF0A84FF);
  static const Color text = Color(0xE0FFFFFF);
  static const Color textDim = Color(0x61FFFFFF);
  static const Color error = Color(0xFFFF453A);
  static const Color success = Color(0xFF30D158);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      primaryColor: accent,
      scaffoldBackgroundColor: background,
      textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).copyWith(
        bodyLarge: const TextStyle(color: text, fontSize: 16),
        bodyMedium: const TextStyle(color: text, fontSize: 14),
        titleLarge: const TextStyle(color: text, fontSize: 18, fontWeight: FontWeight.w600),
      ),
      iconTheme: const IconThemeData(color: textDim),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
    );
  }
}

class GlassContainer extends StatelessWidget {
  final Widget child;
  final double blur;
  final double borderRadius;
  final Color color;
  final BoxBorder? border;
  final EdgeInsetsGeometry? padding;
  final double? width;
  final double? height;

  const GlassContainer({
    Key? key,
    required this.child,
    this.blur = 40,
    this.borderRadius = 16,
    this.color = AppTheme.surface,
    this.border,
    this.padding,
    this.width,
    this.height,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          width: width,
          height: height,
          padding: padding,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(borderRadius),
            border: border ?? Border.all(color: AppTheme.border, width: 0.5),
          ),
          child: child,
        ),
      ),
    );
  }
}
