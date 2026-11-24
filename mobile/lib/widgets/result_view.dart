import 'package:intl/intl.dart';
import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../models.dart';
import '../theme.dart';

/// Full-screen answer after a scan. The colour, the icon and the big title all say the same
/// thing, so the result is clear at arm's length and for people who do not see colours well.
class ResultView extends StatelessWidget {
  const ResultView({super.key, required this.result, required this.recorded, required this.onNext});

  final ScanResult result;

  /// False when the scan was "verify only".
  final bool recorded;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final look = OutcomeLook.of(result.outcome);
    final name = result.outcome.name; // valid, alreadyUsed, campaignQr, ...
    final hintKey = result.outcome == ScanOutcome.valid && !recorded ? 'result_valid_verify_hint' : 'result_${name}_hint';
    final ticket = result.ticket;
    final language = context.session.language;

    return ColoredBox(
      color: look.color,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              Icon(look.icon, size: 110, color: Colors.white),
              const SizedBox(height: 12),
              Semantics(
                liveRegion: true, // screen readers announce the result immediately
                child: Text(
                  context.t('result_$name'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 34, height: 1.1, fontWeight: FontWeight.w800, color: Colors.white),
                ),
              ),
              const SizedBox(height: 10),
              Text(context.t(hintKey), textAlign: TextAlign.center, style: const TextStyle(fontSize: 18, color: Colors.white)),
              const SizedBox(height: 20),
              if (ticket != null)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(ticket.attendeeName, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: AppColors.ink)),
                        const SizedBox(height: 6),
                        Text('${context.t('ticketType')}: ${ticket.ticketType}', style: const TextStyle(fontSize: 16)),
                        if (ticket.seat != null) Text('${context.t('seat')}: ${ticket.seat}', style: const TextStyle(fontSize: 16)),
                        Text('${context.t('ticket')}: ${ticket.code}   ${context.t('order')}: ${ticket.orderNumber}', style: const TextStyle(fontSize: 14, color: AppColors.inkSoft)),
                        if (result.outcome == ScanOutcome.alreadyUsed && ticket.checkedInAt != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Text(
                              context.t('usedAt', {'time': DateFormat('d MMM, HH:mm', language).format(ticket.checkedInAt!)}),
                              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.warn),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              const Spacer(),
              Text(
                '${context.t('checkedIn')}: ${result.stats.checkedIn} / ${result.stats.registered}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 16, color: Colors.white, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: Colors.white, foregroundColor: AppColors.ink, minimumSize: const Size.fromHeight(60)),
                onPressed: onNext,
                child: Text(context.t('scanNext')),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
