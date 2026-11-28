import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../../attendee_models.dart';
import '../../format.dart';
import '../../l10n.dart';
import '../../theme.dart';
import '../../widgets/common.dart';
import 'buyer_details_screen.dart';

class EventDetailScreen extends StatefulWidget {
  const EventDetailScreen({super.key, required this.slug});

  final String slug;

  @override
  State<EventDetailScreen> createState() => _EventDetailScreenState();
}

class _EventDetailScreenState extends State<EventDetailScreen> {
  EventDetail? _event;
  String? _loadProblem;
  bool _started = false;

  final Map<String, int> _quantities = {};
  final _promo = TextEditingController();
  String? _promoCode;

  Quote? _quote;
  String? _quoteProblem;
  Timer? _quoteTimer;
  int _quoteRequest = 0;

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
    _quoteTimer?.cancel();
    _promo.dispose();
    super.dispose();
  }

  Selection get _selection => Selection(eventId: _event!.id, quantities: Map.of(_quantities), promoCode: _promoCode);

  Future<void> _load() async {
    try {
      final event = await context.session.api.event(widget.slug);
      if (mounted) setState(() { _event = event; _loadProblem = null; });
    } on Object catch (error) {
      if (mounted) setState(() => _loadProblem = context.errorText(error));
    }
  }

  void _requote() {
    _quoteTimer?.cancel();
    setState(() { _quote = null; _quoteProblem = null; });
    if (_selection.isEmpty) return;
    _quoteTimer = Timer(const Duration(milliseconds: 300), () async {
      final request = ++_quoteRequest;
      try {
        final quote = await context.session.api.quote(_selection);
        if (mounted && request == _quoteRequest) setState(() => _quote = quote);
      } on Object catch (error) {
        // An older answer must not overwrite a newer one, so only the latest request is shown.
        if (mounted && request == _quoteRequest) setState(() => _quoteProblem = context.errorText(error));
      }
    });
  }

  void _step(TicketOffer offer, int delta) {
    _quantities[offer.id] = ((_quantities[offer.id] ?? 0) + delta).clamp(0, offer.maxPerOrder);
    _requote();
  }

  void _togglePromo() {
    final code = _promo.text.trim();
    _promoCode = _promoCode == null && code.isNotEmpty ? code : null;
    if (_promoCode == null) _promo.clear();
    _requote();
  }

  Future<void> _continue() async {
    if (!await ensureSignedIn(context) || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => BuyerDetailsScreen(event: _event!, selection: _selection, quote: _quote!)));
    if (mounted) _load(); // stock may have changed meanwhile
  }

  @override
  Widget build(BuildContext context) {
    final event = _event;
    if (event == null) {
      return Scaffold(
        appBar: AppBar(),
        body: Center(child: _loadProblem == null ? const CircularProgressIndicator() : ProblemCard(text: _loadProblem!, onRetry: _load)),
      );
    }
    final language = context.session.language;
    final summary = event.summary;
    final canBuy = !summary.isSeated && event.ticketTypes.any((offer) => offer.onSale);
    final quote = _quote;
    return Scaffold(
      appBar: AppBar(title: Text(summary.title, overflow: TextOverflow.ellipsis)),
      body: ListView(
        children: [
          EventImage(url: summary.image, height: 200),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(summary.title, style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w800, color: AppColors.ink)),
                const SizedBox(height: 10),
                Text(
                  '${dateTime(summary.startAt, language)}\n${summary.venue}\n${event.address}',
                  style: const TextStyle(fontSize: 16, color: AppColors.ink, height: 1.45),
                ),
                if (summary.isCancelled) ...[const SizedBox(height: 12), NoteBox.warning(text: context.t('cancelledNote'))],
                const SizedBox(height: 20),
                Text(context.t('tickets'), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: AppColors.ink)),
                const SizedBox(height: 8),
                if (summary.isSeated)
                  NoteBox(text: context.t('seatsOnWebsite'))
                else
                  for (final offer in event.ticketTypes)
                    _OfferRow(offer: offer, quantity: _quantities[offer.id] ?? 0, onStep: (delta) => _step(offer, delta)),
                if (canBuy) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _promo,
                          enabled: _promoCode == null,
                          textCapitalization: TextCapitalization.characters,
                          decoration: InputDecoration(labelText: context.t('promoCode')),
                        ),
                      ),
                      const SizedBox(width: 10),
                      SizedBox(
                        width: 130, // buttons are full-width in the theme; inside a row they need a width
                        child: OutlinedButton(onPressed: _togglePromo, child: Text(_promoCode == null ? context.t('apply') : context.t('removePromo'))),
                      ),
                    ],
                  ),
                ],
                if (quote != null) ...[const SizedBox(height: 16), QuoteCard(quote: quote)],
                if (_quoteProblem != null) ...[const SizedBox(height: 12), ProblemText(_quoteProblem!)],
                if (event.description?.isNotEmpty ?? false) ...[
                  const SizedBox(height: 24),
                  Text(context.t('aboutEvent'), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: AppColors.ink)),
                  const SizedBox(height: 8),
                  Text(event.description!, style: const TextStyle(fontSize: 16, height: 1.45, color: AppColors.ink)),
                ],
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: !canBuy
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: FilledButton(
                  onPressed: quote == null ? null : _continue,
                  child: Text(quote == null ? context.t('total') : '${context.t('continueCheckout')} · ${quote.total == 0 ? context.t('free') : money(quote.total)}'),
                ),
              ),
            ),
    );
  }
}

/// One ticket type with a − / + stepper, or the reason it cannot be bought.
class _OfferRow extends StatelessWidget {
  const _OfferRow({required this.offer, required this.quantity, required this.onStep});

  final TicketOffer offer;
  final int quantity;
  final ValueChanged<int> onStep;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(offer.name, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: AppColors.ink)),
                  Text(offer.price == 0 ? context.t('free') : money(offer.price), style: const TextStyle(fontSize: 16, color: AppColors.skyDeep)),
                  if (!offer.onSale)
                    Text(context.t('unavailable_${offer.unavailableReason}'), style: const TextStyle(color: AppColors.bad, fontWeight: FontWeight.w600)),
                ],
              ),
            ),
            if (offer.onSale) ...[
              IconButton.outlined(tooltip: '${context.t('fewer')}: ${offer.name}', onPressed: quantity > 0 ? () => onStep(-1) : null, icon: const Icon(Icons.remove)),
              SizedBox(width: 34, child: Text('$quantity', textAlign: TextAlign.center, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700))),
              IconButton.filled(
                tooltip: '${context.t('more')}: ${offer.name}',
                onPressed: quantity < offer.maxPerOrder ? () => onStep(1) : null,
                icon: const Icon(Icons.add),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class QuoteCard extends StatelessWidget {
  const QuoteCard({super.key, required this.quote});

  final Quote quote;

  @override
  Widget build(BuildContext context) {
    Widget row(String label, String amount, {bool bold = false}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Expanded(child: Text(label, style: TextStyle(fontSize: bold ? 18 : 15, fontWeight: bold ? FontWeight.w800 : FontWeight.w500))),
          Text(amount, style: TextStyle(fontSize: bold ? 18 : 15, fontWeight: bold ? FontWeight.w800 : FontWeight.w500)),
        ],
      ),
    );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            for (final line in quote.lines) row('${line.name} × ${line.quantity}', money(line.amount)),
            if (quote.discount > 0)
              Text(context.t('discountIncluded', {'amount': money(quote.discount)}), style: const TextStyle(color: AppColors.ok, fontWeight: FontWeight.w600)),
            const Divider(height: 20),
            row(context.t('total'), quote.total == 0 ? context.t('free') : money(quote.total), bold: true),
          ],
        ),
      ),
    );
  }
}
