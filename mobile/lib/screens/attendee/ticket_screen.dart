import 'package:material_ui/material_ui.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../attendee_models.dart';
import '../../format.dart';
import '../../l10n.dart';
import '../../theme.dart';
import '../../widgets/common.dart';

class TicketScreen extends StatelessWidget {
  const TicketScreen({super.key, required this.ticket});

  final Ticket ticket;

  @override
  Widget build(BuildContext context) {
    final payload = ticket.qrPayload;
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(title: Text(context.t('ticketCode', {'code': ticket.code}))),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(ticket.eventTitle, textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.ink)),
          const SizedBox(height: 6),
          Text(
            '${dateTime(ticket.eventStart, context.session.language)}\n${ticket.venue}',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 15, color: AppColors.inkSoft, height: 1.4),
          ),
          const SizedBox(height: 20),
          if (ticket.status == 'valid' && payload != null) ...[
            Center(child: QrImageView(data: payload, size: 280, padding: const EdgeInsets.all(16), backgroundColor: Colors.white)),
            Text(context.t('showAtEntrance'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 15, color: AppColors.inkSoft)),
          ] else if (ticket.status == 'checked_in')
            NoteBox.success(text: context.t('status_checked_in'))
          else
            NoteBox.warning(text: context.t('ticketNotValid')),
          const SizedBox(height: 20),
          Text(
            [ticket.attendeeName, ticket.ticketType, ?ticket.seat].join(' · '),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.ink),
          ),
        ],
      ),
    );
  }
}
