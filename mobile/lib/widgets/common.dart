library;

import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../screens/login_screen.dart';
import '../theme.dart';

class ProblemCard extends StatelessWidget {
  const ProblemCard({super.key, required this.text, this.onRetry});

  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(liveRegion: true, child: Text(text, style: const TextStyle(color: AppColors.bad, fontSize: 16, fontWeight: FontWeight.w600))),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              OutlinedButton(onPressed: onRetry, child: Text(context.t('retry'))),
            ],
          ],
        ),
      ),
    );
  }
}

class ProblemText extends StatelessWidget {
  const ProblemText(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Text(text, style: const TextStyle(color: AppColors.bad, fontSize: 15, fontWeight: FontWeight.w600)),
  );
}

class NoteBox extends StatelessWidget {
  const NoteBox({super.key, required this.text, this.icon = Icons.info_outline, this.color = AppColors.skyDeep, this.background = AppColors.skyPale});

  const NoteBox.success({super.key, required this.text}) : icon = Icons.check_circle, color = AppColors.ok, background = const Color(0xFFE3F4EA);

  const NoteBox.warning({super.key, required this.text}) : icon = Icons.warning_amber, color = AppColors.warn, background = const Color(0xFFFFF1D6);

  final String text;
  final IconData icon;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(12)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: const TextStyle(color: AppColors.ink, fontSize: 15, height: 1.35))),
        ],
      ),
    );
  }
}

class EventImage extends StatelessWidget {
  const EventImage({super.key, required this.url, this.height = 160});

  final String? url;
  final double height;

  @override
  Widget build(BuildContext context) {
    final placeholder = Container(
      height: url == null ? (height < 72 ? height : 72) : height,
      color: AppColors.skyPale,
      alignment: Alignment.center,
      child: const Icon(Icons.confirmation_number_outlined, size: 36, color: AppColors.skyDeep),
    );
    if (url == null) return placeholder;
    return Image.network(
      url!,
      height: height,
      width: double.infinity,
      fit: BoxFit.cover,
      excludeFromSemantics: true,
      errorBuilder: (_, _, _) => placeholder,
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.text, this.color = AppColors.inkSoft});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
      child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 13)),
    );
  }
}

const buttonSpinner = SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white));

Future<bool> ensureSignedIn(BuildContext context) async {
  if (context.session.isSignedIn) return true;
  final signedIn = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const LoginScreen()));
  return signedIn ?? false;
}
