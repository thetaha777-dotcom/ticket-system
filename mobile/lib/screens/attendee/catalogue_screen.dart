import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../../attendee_models.dart';
import '../../format.dart';
import '../../l10n.dart';
import '../../theme.dart';
import '../../widgets/brand_logo.dart';
import '../../widgets/common.dart';
import '../../widgets/language_button.dart';
import 'event_detail_screen.dart';

/// Public events with a search field. Anyone can browse; buying asks to sign in.
class CatalogueScreen extends StatefulWidget {
  const CatalogueScreen({super.key});

  @override
  State<CatalogueScreen> createState() => _CatalogueScreenState();
}

class _CatalogueScreenState extends State<CatalogueScreen> {
  final _search = TextEditingController();
  Timer? _typing;
  List<EventSummary>? _events;
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

  @override
  void dispose() {
    _typing?.cancel();
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final query = _search.text;
    try {
      final events = await context.session.api.listEvents(query: query);
      if (mounted && query == _search.text) setState(() { _events = events; _problem = null; });
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    }
  }

  @override
  Widget build(BuildContext context) {
    final events = _events;
    return Scaffold(
      appBar: AppBar(title: const BrandLogo(height: 30), actions: const [LanguageButton()]),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            TextField(
              controller: _search,
              // Search a moment after typing stops, not on every key press.
              onChanged: (_) {
                _typing?.cancel();
                _typing = Timer(const Duration(milliseconds: 400), _load);
              },
              decoration: InputDecoration(prefixIcon: const Icon(Icons.search), hintText: context.t('searchEvents')),
            ),
            const SizedBox(height: 14),
            if (_problem != null) ProblemCard(text: _problem!, onRetry: _load),
            if (events == null && _problem == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
            if (events != null && events.isEmpty) Text(context.t('noEventsFound'), style: const TextStyle(fontSize: 16)),
            for (final event in events ?? const <EventSummary>[]) _EventCard(event: event),
          ],
        ),
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  const _EventCard({required this.event});

  final EventSummary event;

  @override
  Widget build(BuildContext context) {
    final price = event.priceFrom;
    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => EventDetailScreen(slug: event.slug))),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            EventImage(url: event.image, height: 150),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(shortDateTime(event.startAt, context.session.language), style: const TextStyle(color: AppColors.skyDeep, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(event.title, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: AppColors.ink)),
                  const SizedBox(height: 4),
                  Text(event.venue, style: const TextStyle(color: AppColors.inkSoft, fontSize: 15)),
                  const SizedBox(height: 10),
                  if (event.isCancelled)
                    StatusChip(text: context.t('eventCancelledShort'), color: AppColors.bad)
                  else if (price == 0)
                    StatusChip(text: context.t('free'), color: AppColors.ok)
                  else if (price != null)
                    Text(context.t('priceFromAmount', {'amount': money(price)}), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16))
                  else
                    StatusChip(text: context.t('salesClosed')),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
