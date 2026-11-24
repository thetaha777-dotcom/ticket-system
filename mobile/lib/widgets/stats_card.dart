import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../models.dart';
import '../theme.dart';

/// Registered / checked-in / still-to-arrive counters with a progress bar.
class StatsCard extends StatelessWidget {
  const StatsCard({super.key, required this.stats});

  final CheckInStats stats;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                _Number(label: context.t('checkedIn'), value: stats.checkedIn, emphasised: true),
                _Number(label: context.t('registered'), value: stats.registered),
                _Number(label: context.t('remaining'), value: stats.remaining),
              ],
            ),
            const SizedBox(height: 14),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: stats.progress,
                minHeight: 10,
                backgroundColor: AppColors.skyPale,
                color: AppColors.skyDeep,
                semanticsLabel: context.t('checkedIn'),
                semanticsValue: '${stats.checkedIn} / ${stats.registered}',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Number extends StatelessWidget {
  const _Number({required this.label, required this.value, this.emphasised = false});

  final String label;
  final int value;
  final bool emphasised;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 13, color: AppColors.inkSoft)),
          Text(
            '$value',
            style: TextStyle(fontSize: emphasised ? 34 : 26, fontWeight: FontWeight.w700, color: AppColors.ink, fontFeatures: const [FontFeature.tabularFigures()]),
          ),
        ],
      ),
    );
  }
}
