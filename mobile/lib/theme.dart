library;

import 'package:material_ui/material_ui.dart';

import 'models.dart';

abstract final class AppColors {
  static const ink = Color(0xFF15302C); // text: a very dark teal
  static const inkSoft = Color(0xFF4F625E);
  static const skyDeep = Color(0xFF20655F); // brand teal: buttons, links, highlights
  static const skyPale = Color(0xFFDCEDE8);
  static const sun = Color(0xFFFAC55B); // brand gold
  static const sunPale = Color(0xFFFFF8B6); // brand pale yellow
  static const mist = Color(0xFFFFF8B6); // page background
  static const line = Color(0xFFE3D99C);
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
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      indicatorColor: AppColors.sunPale,
      iconTheme: WidgetStateProperty.resolveWith(
        (states) => IconThemeData(color: states.contains(WidgetState.selected) ? AppColors.skyDeep : AppColors.inkSoft),
      ),
    ),
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
