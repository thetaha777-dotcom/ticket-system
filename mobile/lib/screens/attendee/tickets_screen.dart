import 'package:material_ui/material_ui.dart';

import '../../attendee_models.dart';
import '../../format.dart';
import '../../l10n.dart';
import '../../theme.dart';
import '../../widgets/common.dart';
import 'ticket_screen.dart';

class TicketsScreen extends StatefulWidget {
  const TicketsScreen({super.key});

  @override
  State<TicketsScreen> createState() => _TicketsScreenState();
}

class _TicketsScreenState extends State<TicketsScreen> {
  List<Ticket>? _tickets;
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
    try {
      final tickets = await context.session.api.myTickets();
      if (mounted) setState(() { _tickets = [for (final t in tickets) if (t.isCurrent) t]; _problem = null; });
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    }
  }

  @override
  Widget build(BuildContext context) {
    final tickets = _tickets;
    return Scaffold(
      appBar: AppBar(
        title: Text(context.t('tabTickets')),
        actions: [IconButton(tooltip: context.t('signOut'), icon: const Icon(Icons.logout), onPressed: context.session.signOut)],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            if (_problem != null) ProblemCard(text: _problem!, onRetry: _load),
            if (tickets == null && _problem == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
            if (tickets != null && tickets.isEmpty) Text(context.t('noUpcomingTickets'), style: const TextStyle(fontSize: 16)),
            for (final ticket in tickets ?? const <Ticket>[]) TicketTile(ticket: ticket),
          ],
        ),
      ),
    );
  }
}

class TicketTile extends StatelessWidget {
  const TicketTile({super.key, required this.ticket});

  final Ticket ticket;

  @override
  Widget build(BuildContext context) {
    final details = [shortDateTime(ticket.eventStart, context.session.language), '${ticket.ticketType} · ${ticket.attendeeName}', ?ticket.seat];
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        leading: const Icon(Icons.qr_code_2, size: 36, color: AppColors.ink),
        title: Text(ticket.eventTitle, style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.ink)),
        subtitle: Text(details.join('\n')),
        trailing: StatusChip(text: context.t('status_${ticket.status}'), color: ticket.status == 'valid' ? AppColors.ok : AppColors.skyDeep),
        onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => TicketScreen(ticket: ticket))),
      ),
    );
  }
}
