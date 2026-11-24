/// Colours and theme shared with the BiletFlow web app ("sky and sun" on deep ink).
library;

import 'package:material_ui/material_ui.dart';

import 'models.dart';

abstract final class AppColors {
  static const ink = Color(0xFF12233D);
  static const inkSoft = Color(0xFF5B6B82);
  static const skyDeep = Color(0xFF00728F);
  static const skyPale = Color(0xFFD9F1F6);
  static const sun = Color(0xFFFFC233);
  static const mist = Color(0xFFEEF4F6);
  static const line = Color(0xFFD5DEE6);
  static const ok = Color(0xFF17794D);
  static const warn = Color(0xFF9A5B00);
  static const bad = Color(0xFFB42A25);
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.skyDeep,
    primary: AppColors.skyDeep,
    onPrimary: Colors.white,
    secondary: AppColors.sun,
    onSecondary: AppColors.ink,
    surface: Colors.white,
    onSurface: AppColors.ink,
    error: AppColors.bad,
  );
  return ThemeData(
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.mist,
    appBarTheme: const AppBarTheme(backgroundColor: Colors.white, foregroundColor: AppColors.ink, elevation: 0, scrolledUnderElevation: 1),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: const BorderSide(color: AppColors.line)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: AppColors.line)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: AppColors.line)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52), // large touch targets: the app is used standing at a door
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        foregroundColor: AppColors.ink,
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        side: const BorderSide(color: AppColors.line),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
  );
}

/// How a scan outcome is shown: a colour AND an icon, so it is clear without relying on colour alone.
class OutcomeLook {
  const OutcomeLook(this.color, this.icon);
  final Color color;
  final IconData icon;

  static OutcomeLook of(ScanOutcome outcome) => switch (outcome) {
    ScanOutcome.valid => const OutcomeLook(AppColors.ok, Icons.check_circle),
    ScanOutcome.alreadyUsed => const OutcomeLook(AppColors.warn, Icons.history),
    ScanOutcome.cancelled || ScanOutcome.refunded => const OutcomeLook(AppColors.bad, Icons.block),
    ScanOutcome.wrongEvent => const OutcomeLook(AppColors.bad, Icons.event_busy),
    ScanOutcome.campaignQr => const OutcomeLook(AppColors.bad, Icons.local_offer),
    ScanOutcome.invalid => const OutcomeLook(AppColors.bad, Icons.cancel),
  };
}
