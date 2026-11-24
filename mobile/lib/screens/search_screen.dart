import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../models.dart';
import '../theme.dart';

/// Manual attendee search, for guests who cannot show a QR code,
/// with "Check in" and (where allowed) "Undo check-in".
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key, required this.event});

  final StaffEvent event;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _query = TextEditingController();
  Timer? _debounce;
  List<TicketInfo>? _tickets;
  String? _problem;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      _search();
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _query.dispose();
    super.dispose();
  }

  /// Wait until typing pauses for 350 ms, then ask the server.
  void _onChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), _search);
  }

  Future<void> _search() async {
    final api = context.session.api;
    try {
      final tickets = await api.search(widget.event.id, _query.text);
      if (!mounted) return;
      setState(() {
        _tickets = tickets;
        _problem = null;
      });
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    }
  }

  Future<void> _act(TicketInfo ticket, {required bool undo}) async {
    final api = context.session.api;
    final messenger = ScaffoldMessenger.of(context);
    final done = context.t(undo ? 'done_undo' : 'done_checkIn');
    try {
      undo ? await api.undoCheckIn(widget.event.id, ticket.id) : await api.manualCheckIn(widget.event.id, ticket.id);
      messenger.showSnackBar(SnackBar(content: Text('${ticket.attendeeName}: $done')));
    } on Object catch (error) {
      if (!mounted) return;
      messenger.showSnackBar(SnackBar(content: Text(context.errorText(error)), backgroundColor: AppColors.bad));
    }
    await _search();
  }

  void _openTicket(TicketInfo ticket) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(ticket.attendeeName, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: AppColors.ink)),
              Text(ticket.attendeeEmail, style: const TextStyle(color: AppColors.inkSoft)),
              const SizedBox(height: 10),
              Text('${context.t('ticketType')}: ${ticket.ticketType}', style: const TextStyle(fontSize: 16)),
              if (ticket.seat != null) Text('${context.t('seat')}: ${ticket.seat}', style: const TextStyle(fontSize: 16)),
              Text('${context.t('ticket')}: ${ticket.code}', style: const TextStyle(fontSize: 16)),
              Text('${context.t('order')}: ${ticket.orderNumber}', style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 10),
              _StatusChip(status: ticket.status),
              const SizedBox(height: 16),
              if (ticket.status == 'valid')
                FilledButton.icon(
                  onPressed: () {
                    Navigator.of(sheetContext).pop();
                    _act(ticket, undo: false);
                  },
                  icon: const Icon(Icons.how_to_reg),
                  label: Text(context.t('checkInNow')),
                ),
              if (ticket.status == 'checked_in' && widget.event.canUndo)
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.of(sheetContext).pop();
                    _act(ticket, undo: true);
                  },
                  icon: const Icon(Icons.undo),
                  label: Text(context.t('undoCheckIn')),
                ),
              if (ticket.status == 'checked_in' && !widget.event.canUndo)
                Text(context.t('undoNotAllowed'), style: const TextStyle(color: AppColors.inkSoft)),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tickets = _tickets;
    return Scaffold(
      appBar: AppBar(title: Text(context.t('search'))),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _query,
              autofocus: true,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(prefixIcon: const Icon(Icons.search), labelText: context.t('searchHint')),
              onChanged: _onChanged,
              onSubmitted: (_) => _search(),
            ),
          ),
          if (_problem != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(_problem!, style: const TextStyle(color: AppColors.bad, fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          Expanded(
            child: tickets == null
                ? const Center(child: CircularProgressIndicator())
                : tickets.isEmpty
                ? Center(child: Text(context.t('noMatches'), style: const TextStyle(fontSize: 16, color: AppColors.inkSoft)))
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    itemCount: tickets.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final ticket = tickets[index];
                      return Card(
                        clipBehavior: Clip.antiAlias,
                        child: ListTile(
                          onTap: () => _openTicket(ticket),
                          title: Text(ticket.attendeeName, style: const TextStyle(fontWeight: FontWeight.w700)),
                          subtitle: Text('${ticket.ticketType}${ticket.seat == null ? '' : ', ${ticket.seat}'}\n${ticket.code}'),
                          isThreeLine: true,
                          trailing: _StatusChip(status: ticket.status),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (status) {
      'checked_in' => (AppColors.ok, Icons.check_circle),
      'valid' => (AppColors.skyDeep, Icons.radio_button_unchecked),
      _ => (AppColors.bad, Icons.block),
    };
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18, color: color),
        const SizedBox(width: 4),
        Text(context.t('status_$status'), style: TextStyle(color: color, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
