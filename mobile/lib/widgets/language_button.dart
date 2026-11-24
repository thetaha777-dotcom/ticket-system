import 'package:material_ui/material_ui.dart';

import '../l10n.dart';

/// App-bar menu that switches the interface between Kazakh, Russian and English.
class LanguageButton extends StatelessWidget {
  const LanguageButton({super.key});

  static const _names = {'kk': 'Қазақша', 'ru': 'Русский', 'en': 'English'};

  @override
  Widget build(BuildContext context) {
    final session = context.session;
    return PopupMenuButton<String>(
      tooltip: context.t('language'),
      icon: const Icon(Icons.language),
      initialValue: session.language,
      onSelected: session.setLanguage,
      itemBuilder: (_) => [for (final entry in _names.entries) PopupMenuItem(value: entry.key, child: Text(entry.value))],
    );
  }
}
