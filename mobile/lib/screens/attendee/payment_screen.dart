import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../../attendee_models.dart';
import '../../format.dart';
import '../../l10n.dart';
import '../../theme.dart';
import '../../widgets/common.dart';
import 'tickets_screen.dart';

class PaymentScreen extends StatefulWidget {
  const PaymentScreen({super.key, required this.order, required this.title});

  final Order order;
  final String title;

  @override
  State<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends State<PaymentScreen> {
  late Order _order = widget.order;
  late final Timer _ticker;
  bool _busy = false;
  String? _problem;

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
  }

  @override
  void dispose() {
    _ticker.cancel();
    super.dispose();
  }

  Duration get _left => _order.expiresAt?.difference(DateTime.now()) ?? Duration.zero;

  void _tick() {
    if (!_order.isPending) return;
    setState(() {}); // redraw the countdown
    if (_left.inSeconds <= 0) _refresh();
  }

  Future<void> _refresh() async {
    try {
      final order = await context.session.api.order(_order.id);
      if (mounted) setState(() => _order = order);
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    }
  }

  Future<void> _pay(bool succeed) async {
    setState(() { _busy = true; _problem = null; });
    try {
      final order = await context.session.api.pay(_order.id, succeed: succeed);
      if (mounted) setState(() => _order = order);
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = _order;
    return Scaffold(
      appBar: AppBar(title: Text(context.t(order.isCompleted ? 'orderTickets' : 'checkoutTitle'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(widget.title, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800, color: AppColors.ink)),
          const SizedBox(height: 16),
          if (order.isCompleted) ...[
            NoteBox.success(text: order.total == 0 ? context.t('registeredDone') : context.t('paid')),
            const SizedBox(height: 12),
            for (final ticket in order.tickets) TicketTile(ticket: ticket),
          ] else if (order.isPending) ...[
            NoteBox(text: '${context.t('heldFor')}  ${countdown(_left)}', icon: Icons.timer_outlined),
            const SizedBox(height: 16),
            Text(context.t('demoText'), style: const TextStyle(fontSize: 15, color: AppColors.inkSoft)),
            const SizedBox(height: 16),
            FilledButton(onPressed: _busy ? null : () => _pay(true), child: Text(context.t('paySuccess', {'amount': money(order.total)}))),
            const SizedBox(height: 10),
            OutlinedButton(onPressed: _busy ? null : () => _pay(false), child: Text(context.t('payFailure'))),
            if (order.lastPaymentFailed) ...[const SizedBox(height: 12), NoteBox.warning(text: context.t('declined'))],
          ] else
            NoteBox.warning(text: context.t('holdExpired')),
          if (_problem != null) ...[const SizedBox(height: 12), ProblemText(_problem!)],
        ],
      ),
    );
  }
}
