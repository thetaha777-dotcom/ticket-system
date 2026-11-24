import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/stats_card.dart';
import 'activity_screen.dart';
import 'scan_screen.dart';
import 'search_screen.dart';

/// Home of one event: live counters and the three things staff do (scan, search, look at activity).
class EventScreen extends StatefulWidget {
  const EventScreen({super.key, required this.event});

  final StaffEvent event;

  @override
  State<EventScreen> createState() => _EventScreenState();
}

class _EventScreenState extends State<EventScreen> {
  late CheckInStats _stats = widget.event.stats;
  Timer? _timer;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      _refresh();
      // Other doors check people in too: re-read the shared counters every 10 seconds.
      _timer = Timer.periodic(const Duration(seconds: 10), (_) => _refresh());
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    final api = context.session.api;
    try {
      final stats = await api.stats(widget.event.id);
      if (mounted) setState(() => _stats = stats);
    } on Object {
      // Keep the last known numbers; the next refresh or scan will update them.
    }
  }

  Future<void> _open(Widget screen) async {
    await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => screen));
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final event = widget.event;
    return Scaffold(
      appBar: AppBar(
        title: Text(event.title),
        actions: [IconButton(tooltip: context.t('refresh'), icon: const Icon(Icons.refresh), onPressed: _refresh)],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('${event.venueName}, ${event.venueCity}', style: const TextStyle(color: AppColors.inkSoft, fontSize: 15)),
            const SizedBox(height: 12),
            StatsCard(stats: _stats),
            const SizedBox(height: 20),
            FilledButton.icon(
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(64), backgroundColor: AppColors.sun, foregroundColor: AppColors.ink),
              onPressed: () => _open(ScanScreen(event: event)),
              icon: const Icon(Icons.qr_code_scanner, size: 28),
              label: Text(context.t('scan')),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _open(SearchScreen(event: event)),
              icon: const Icon(Icons.person_search),
              label: Text(context.t('search')),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _open(ActivityScreen(event: event)),
              icon: const Icon(Icons.list_alt),
              label: Text(context.t('activity')),
            ),
          ],
        ),
      ),
    );
  }
}
