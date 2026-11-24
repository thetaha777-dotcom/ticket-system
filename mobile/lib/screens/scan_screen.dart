import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../l10n.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/result_view.dart';
import 'search_screen.dart';

/// Camera scanner. Each QR code is sent to the server, which decides whether it admits:
/// the phone itself never decides, so a ticket cannot be used twice at two doors.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key, required this.event});

  final StaffEvent event;

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  // The camera reports what it sees a few times per second; _onDetect ignores codes while one is being checked.
  final _controller = MobileScannerController(detectionSpeed: DetectionSpeed.normal, detectionTimeoutMs: 700, formats: const [BarcodeFormat.qrCode]);

  bool _recordEntry = true;
  bool _checking = false;
  bool _resultWasRecorded = true;
  ScanResult? _result;
  String? _problem;
  late CheckInStats _stats = widget.event.stats;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_checking || _result != null) return; // one ticket at a time
    final payload = capture.barcodes.firstOrNull?.rawValue;
    if (payload == null || payload.isEmpty) return;

    final api = context.session.api;
    setState(() {
      _checking = true;
      _problem = null;
    });
    final recorded = _recordEntry;
    try {
      final result = await api.scan(widget.event.id, payload, checkIn: recorded);
      if (!mounted) return;
      // A strong buzz for "do not admit", a light one for "welcome".
      if (result.outcome.admits) {
        HapticFeedback.mediumImpact();
      } else {
        HapticFeedback.vibrate();
      }
      setState(() {
        _result = result;
        _resultWasRecorded = recorded;
        _stats = result.stats;
      });
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  void _next() => setState(() => _result = null);

  @override
  Widget build(BuildContext context) {
    final result = _result;
    // The scanner stays mounted underneath the result, so the camera is ready for the next guest at once.
    return Stack(
      children: [
        _buildScanner(context),
        if (result != null) Positioned.fill(child: Material(child: ResultView(result: result, recorded: _resultWasRecorded, onNext: _next))),
      ],
    );
  }

  Widget _buildScanner(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(widget.event.title),
        actions: [
          IconButton(tooltip: context.t('torch'), icon: const Icon(Icons.flashlight_on), onPressed: _controller.toggleTorch),
          IconButton(
            tooltip: context.t('search'),
            icon: const Icon(Icons.person_search),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => SearchScreen(event: widget.event))),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Stack(
              fit: StackFit.expand,
              children: [
                MobileScanner(
                  controller: _controller,
                  onDetect: _onDetect,
                  errorBuilder: (context, error) => _CameraProblem(text: context.t('cameraError')),
                ),
                // Aiming frame
                Center(
                  child: Container(
                    width: 250,
                    height: 250,
                    decoration: BoxDecoration(border: Border.all(color: AppColors.sun, width: 4), borderRadius: BorderRadius.circular(20)),
                  ),
                ),
                if (_checking)
                  ColoredBox(
                    color: Colors.black54,
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const CircularProgressIndicator(color: Colors.white),
                          const SizedBox(height: 12),
                          Text(context.t('checking'), style: const TextStyle(color: Colors.white, fontSize: 18)),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
            child: SafeArea(
              top: false,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_problem != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Semantics(
                        liveRegion: true,
                        child: Text(_problem!, style: const TextStyle(color: AppColors.bad, fontSize: 16, fontWeight: FontWeight.w600)),
                      ),
                    ),
                  Text(_problem == null ? context.t('pointCamera') : '', style: const TextStyle(fontSize: 16, color: AppColors.ink)),
                  const SizedBox(height: 6),
                  Text(
                    '${context.t('checkedIn')}: ${_stats.checkedIn} / ${_stats.registered}',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.ink),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(context.t('recordEntry')),
                    subtitle: _recordEntry ? null : Text(context.t('verifyOnly')),
                    value: _recordEntry,
                    onChanged: (value) => setState(() => _recordEntry = value),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CameraProblem extends StatelessWidget {
  const _CameraProblem({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(text, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 17)),
        ),
      ),
    );
  }
}
