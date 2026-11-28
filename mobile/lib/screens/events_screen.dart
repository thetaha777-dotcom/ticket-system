import 'package:intl/intl.dart';
import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/language_button.dart';
import 'event_screen.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  List<StaffEvent>? _events;
  String? _problem;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      _load();
    }
  }

  Future<void> _load() async {
    final session = context.session;
    try {
      final events = await session.api.events();
      if (!mounted) return;
      setState(() {
        _events = events;
        _problem = null;
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _problem = context.errorText(error));
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.session;
    return Scaffold(
      appBar: AppBar(
        title: Text(context.t('tabCheckIn')),
        actions: [
          const LanguageButton(),
          IconButton(tooltip: context.t('signOut'), icon: const Icon(Icons.logout), onPressed: session.signOut),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(session.user?.name ?? '', style: const TextStyle(color: AppColors.inkSoft, fontSize: 15)),
            ),
            if (_problem != null) _Problem(text: _problem!, onRetry: _load),
            if (_events == null && _problem == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
            if (_events != null && _events!.isEmpty)
              Card(
                child: Padding(padding: const EdgeInsets.all(20), child: Text(context.t('noEvents'), style: const TextStyle(fontSize: 16))),
              ),
            for (final event in _events ?? const <StaffEvent>[])
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _EventCard(event: event, onReturn: _load),
              ),
          ],
        ),
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  const _EventCard({required this.event, required this.onReturn});

  final StaffEvent event;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final language = context.session.language;
    final when = DateFormat('d MMMM, HH:mm', language).format(event.startAt);
    final active = event.eventClass == 'active';
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () async {
          await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => EventScreen(event: event)));
          onReturn(); // counters may have changed while scanning
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(active ? Icons.play_circle : Icons.schedule, size: 18, color: active ? AppColors.ok : AppColors.inkSoft),
                  const SizedBox(width: 6),
                  Text(
                    context.t(active ? 'activeNow' : 'upcoming'),
                    style: TextStyle(fontWeight: FontWeight.w600, color: active ? AppColors.ok : AppColors.inkSoft),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(event.title, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w700, color: AppColors.ink)),
              const SizedBox(height: 4),
              Text('$when\n${event.venueName}, ${event.venueCity}', style: const TextStyle(color: AppColors.inkSoft, fontSize: 15, height: 1.35)),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(value: event.stats.progress, minHeight: 8, backgroundColor: AppColors.skyPale, color: AppColors.skyDeep),
              ),
              const SizedBox(height: 6),
              Text(
                '${context.t('checkedIn')}: ${event.stats.checkedIn} / ${event.stats.registered}',
                style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.ink),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Problem extends StatelessWidget {
  const _Problem({required this.text, required this.onRetry});

  final String text;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(text, style: const TextStyle(color: AppColors.bad, fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: Text(context.t('retry'))),
          ],
        ),
      ),
    );
  }
}
