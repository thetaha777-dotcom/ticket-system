import 'package:material_ui/material_ui.dart';

import '../../attendee_models.dart';
import '../../l10n.dart';
import '../../theme.dart';
import '../../widgets/common.dart';
import '../register_screen.dart';
import 'event_detail_screen.dart';
import 'payment_screen.dart';

/// Buyer name, email and phone, then the order is started: the server reserves the tickets for
/// 10 minutes (a free order is completed at once). Every ticket carries the buyer's name.
class BuyerDetailsScreen extends StatefulWidget {
  const BuyerDetailsScreen({super.key, required this.event, required this.selection, required this.quote});

  final EventDetail event;
  final Selection selection;
  final Quote quote;

  @override
  State<BuyerDetailsScreen> createState() => _BuyerDetailsScreenState();
}

class _BuyerDetailsScreenState extends State<BuyerDetailsScreen> {
  final _form = GlobalKey<FormState>();
  late final _name = TextEditingController(text: context.session.user?.name);
  late final _email = TextEditingController(text: context.session.user?.email);
  final _phone = TextEditingController();
  bool _busy = false;
  String? _problem;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _busy = true; _problem = null; });
    try {
      final order = await context.session.api.createOrder(widget.selection, name: _name.text, email: _email.text, phone: _phone.text);
      if (mounted) await Navigator.of(context).pushReplacement(MaterialPageRoute<void>(builder: (_) => PaymentScreen(order: order, title: widget.event.summary.title)));
    } on Object catch (error) {
      // For example sold_out: the buyer goes back, and the event page reloads.
      if (mounted) setState(() => _problem = context.errorText(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final free = widget.quote.total == 0;
    return Scaffold(
      appBar: AppBar(title: Text(context.t('yourDetails'))),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(widget.event.summary.title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.ink)),
            const SizedBox(height: 12),
            QuoteCard(quote: widget.quote),
            const SizedBox(height: 16),
            TextFormField(
              controller: _name,
              decoration: InputDecoration(labelText: context.t('buyerName')),
              validator: (value) => validateRequired(context, value),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _email,
              decoration: InputDecoration(labelText: context.t('buyerEmail')),
              keyboardType: TextInputType.emailAddress,
              validator: (value) => validateEmail(context, value),
            ),
            const SizedBox(height: 12),
            TextFormField(controller: _phone, decoration: InputDecoration(labelText: context.t('buyerPhone')), keyboardType: TextInputType.phone),
            const SizedBox(height: 12),
            if (!free) NoteBox(text: context.t('holdHint')),
            if (_problem != null) ...[const SizedBox(height: 12), ProblemText(_problem!)],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: _busy ? buttonSpinner : Text(free ? context.t('registerFree') : context.t('toPayment')),
            ),
          ],
        ),
      ),
    );
  }
}
