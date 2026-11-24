// Translations, session handling and the screens that need no camera.
import 'dart:convert';

import 'package:biletflow_checkin/api.dart';
import 'package:biletflow_checkin/l10n.dart';
import 'package:biletflow_checkin/main.dart';
import 'package:biletflow_checkin/models.dart';
import 'package:biletflow_checkin/session.dart';
import 'package:biletflow_checkin/theme.dart';
import 'package:biletflow_checkin/widgets/result_view.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:material_ui/material_ui.dart';

http.Response _json(Object body, [int status = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status, headers: {'content-type': 'application/json'});

const _user = {'id': 'u1', 'name': 'Saule Staff', 'email': 'staff@example.com', 'role': 'event_admin'};
const _event = {
  'id': 'e1', 'title': 'Jazz Evening on the Roof', 'start_at': '2026-12-12T14:00:00Z', 'end_at': '2026-12-12T18:00:00Z',
  'timezone': 'Asia/Almaty', 'status': 'published', 'event_class': 'upcoming', 'venue_name': 'Skyline Rooftop',
  'venue_city': 'Astana', 'can_undo': true, 'stats': {'registered': 21, 'checked_in': 3, 'remaining': 18},
};

/// A fake BiletFlow server for widget tests.
MockClient _server({bool wrongPassword = false}) => MockClient((request) async {
  final path = request.url.path;
  if (path.endsWith('/auth/login')) {
    return wrongPassword
        ? _json({'detail': 'Incorrect email or password', 'code': 'invalid_credentials'}, 401)
        : _json({'access_token': 'token-1', 'user': _user});
  }
  if (path.endsWith('/auth/me')) return _json(_user);
  if (path.endsWith('/checkin/events')) return _json([_event]);
  return _json({'detail': 'not found', 'code': 'not_found'}, 404);
});

Session _session(MockClient client, {MemoryStore? store, String language = 'en'}) => Session(
  store: store ?? MemoryStore(),
  api: ApiClient(baseUrl: 'http://server:8000', httpClient: client),
  deviceLanguage: language,
);

void main() {
  setUpAll(() => initializeDateFormatting());

  test('every language has exactly the same texts', () {
    final english = translations['en']!.keys.toSet();
    for (final language in supportedLanguages) {
      expect(translations[language]!.keys.toSet(), english, reason: 'keys of "$language" differ from English');
    }
    expect(translate('ru', 'by', {'name': 'Сауле'}), 'отметил(а) Сауле');
    expect(translate('kk', 'no_such_key'), 'no_such_key');
  });

  test('every scan outcome has a title, a hint and a look', () {
    for (final outcome in ScanOutcome.values) {
      expect(translations['en'], contains('result_${outcome.name}'));
      expect(translations['en'], contains('result_${outcome.name}_hint'));
      expect(OutcomeLook.of(outcome).icon, isNotNull);
    }
    expect(OutcomeLook.of(ScanOutcome.valid).color, AppColors.ok);
    expect(OutcomeLook.of(ScanOutcome.campaignQr).color, AppColors.bad);
  });

  test('session restores a saved token and forgets a rejected one', () async {
    final store = MemoryStore()..values.addAll({'token': 'saved', 'language': 'kk', 'server_url': 'http://other:9000'});
    final session = _session(_server(), store: store);
    await session.restore();
    expect(session.isSignedIn, isTrue);
    expect(session.language, 'kk');
    expect(session.serverUrl, 'http://other:9000');

    final rejected = _session(MockClient((_) async => _json({'detail': 'expired', 'code': 'not_authenticated'}, 401)), store: store);
    await rejected.restore();
    expect(rejected.isSignedIn, isFalse);
    expect(store.values.containsKey('token'), isFalse);
  });

  testWidgets('sign-in shows the assigned events', (tester) async {
    final session = _session(_server());
    await session.restore();
    await tester.pumpWidget(CheckInApp(session: session));
    expect(find.text('Sign in to check tickets'), findsOneWidget);

    // empty form: validation messages, no request
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pump();
    expect(find.text('Fill in this field'), findsNWidgets(2));

    await tester.enterText(find.widgetWithText(TextFormField, 'Email'), 'staff@example.com');
    await tester.enterText(find.widgetWithText(TextFormField, 'Password'), 'Demo12345');
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();

    expect(find.text('My events'), findsOneWidget);
    expect(find.text('Jazz Evening on the Roof'), findsOneWidget);
    expect(find.text('Checked in: 3 / 21'), findsOneWidget);
    expect(session.store.read('token'), completion('token-1'));
  });

  testWidgets('a wrong password shows a translated error', (tester) async {
    final session = _session(_server(wrongPassword: true), language: 'ru');
    await session.restore();
    await tester.pumpWidget(CheckInApp(session: session));
    await tester.enterText(find.widgetWithText(TextFormField, 'Email'), 'staff@example.com');
    await tester.enterText(find.widgetWithText(TextFormField, 'Пароль'), 'wrong');
    await tester.tap(find.widgetWithText(FilledButton, 'Войти'));
    await tester.pumpAndSettle();
    expect(find.text('Неверный email или пароль.'), findsOneWidget);
    expect(session.isSignedIn, isFalse);
  });

  testWidgets('the result screen says clearly when a promo code is scanned', (tester) async {
    final session = _session(_server(), language: 'en');
    var next = 0;
    const result = ScanResult(
      outcome: ScanOutcome.campaignQr,
      message: 'promo',
      stats: CheckInStats(registered: 21, checkedIn: 3, remaining: 18),
    );
    await tester.pumpWidget(SessionScope(
      session: session,
      child: MaterialApp(home: Scaffold(body: ResultView(result: result, recorded: true, onNext: () => next++))),
    ));
    expect(find.text('Promo code, not a ticket'), findsOneWidget);
    expect(find.byIcon(Icons.local_offer), findsOneWidget);
    expect(find.text('Checked in: 3 / 21'), findsOneWidget);
    await tester.tap(find.text('Scan next ticket'));
    expect(next, 1);
  });
}
