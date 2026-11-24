/// BiletFlow Check-in: the mobile app Event Admins use to verify tickets at the entrance.
///
/// Flow of screens:  sign in  ->  my assigned events  ->  one event (counters)  ->  scan / search / activity
library;

import 'package:intl/date_symbol_data_local.dart';
import 'package:material_ui/material_ui.dart';

import 'l10n.dart';
import 'screens/events_screen.dart';
import 'screens/login_screen.dart';
import 'session.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting(); // month and weekday names for kk / ru / en
  final deviceLanguage = WidgetsBinding.instance.platformDispatcher.locale.languageCode;
  final session = Session(store: const SecureStore(), deviceLanguage: deviceLanguage);
  runApp(CheckInApp(session: session));
  await session.restore();
}

class CheckInApp extends StatelessWidget {
  const CheckInApp({super.key, required this.session});

  final Session session;

  @override
  Widget build(BuildContext context) {
    return SessionScope(
      session: session,
      child: ListenableBuilder(
        listenable: session,
        builder: (context, _) => MaterialApp(
          title: 'BiletFlow Check-in',
          debugShowCheckedModeBanner: false,
          theme: buildTheme(),
          locale: Locale(session.language),
          supportedLocales: const [Locale('kk'), Locale('ru'), Locale('en')],
          localizationsDelegates: GlobalMaterialLocalizations.delegates,
          home: !session.ready
              ? const Scaffold(body: Center(child: CircularProgressIndicator()))
              : session.isSignedIn
              ? const EventsScreen()
              : const LoginScreen(),
        ),
      ),
    );
  }
}
