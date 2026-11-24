import 'package:intl/intl.dart';
import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../models.dart';
import '../theme.dart';

/// Latest check-ins and reversals from every device, read from the central platform.
class ActivityScreen extends StatefulWidget {
  const ActivityScreen({super.key, required this.event});

  final StaffEvent event;

  @override
  State<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends State<ActivityScreen> {
  List<ActivityRecord>? _records;
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
    final api = context.session.api;
    try {
      final records = await api.recent(widget.event.id);
      if (!mounted) return;
      setState(() {
        _records = records;
        _problem = null;
      });
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    }
  }

  @override
  Widget build(BuildContext context) {
    final records = _records;
    final time = DateFormat('HH:mm:ss', context.session.language);
    return Scaffold(
      appBar: AppBar(title: Text(context.t('activity'))),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            if (_problem != null) Text(_problem!, style: const TextStyle(color: AppColors.bad, fontSize: 16, fontWeight: FontWeight.w600)),
            if (records == null && _problem == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
            if (records != null && records.isEmpty) Text(context.t('noActivity'), style: const TextStyle(fontSize: 16, color: AppColors.inkSoft)),
            for (final record in records ?? const <ActivityRecord>[])
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Card(
                  child: ListTile(
                    leading: Icon(
                      record.action == 'undo' ? Icons.undo : Icons.check_circle,
                      color: record.action == 'undo' ? AppColors.warn : AppColors.ok,
                    ),
                    title: Text(record.attendeeName, style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text(
                      '${context.t('action_${record.action}')} (${context.t('method_${record.method}')}), ${record.ticketCode}\n'
                      '${context.t('by', {'name': record.staffName})}',
                    ),
                    isThreeLine: true,
                    trailing: Text(time.format(record.createdAt), style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()])),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
