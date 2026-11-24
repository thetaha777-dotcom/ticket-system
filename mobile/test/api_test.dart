// Tests of the API client against a fake HTTP server (no network needed).
import 'dart:convert';

import 'package:biletflow_checkin/api.dart';
import 'package:biletflow_checkin/models.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _stats = {'registered': 10, 'checked_in': 4, 'remaining': 6};
const _ticket = {
  'id': 't-1', 'code': 'ABCD-EFGH', 'status': 'checked_in', 'attendee_name': 'Aruzhan Bekova',
  'attendee_email': 'aruzhan@example.com', 'ticket_type': 'Standard', 'seat': 'VIP · row 2 · seat 4',
  'order_number': 'BF-12345678', 'checked_in_at': '2026-12-12T14:05:00Z',
};

http.Response _json(Object body, [int status = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status, headers: {'content-type': 'application/json'});

void main() {
  test('login stores the token and sends it with later requests', () async {
    final seen = <http.Request>[];
    final api = ApiClient(
      baseUrl: 'http://server:8000/',
      httpClient: MockClient((request) async {
        seen.add(request);
        if (request.url.path.endsWith('/auth/login')) {
          return _json({
            'access_token': 'token-123',
            'user': {'id': 'u1', 'name': 'Saule', 'email': 'staff@example.com', 'role': 'event_admin'},
          });
        }
        return _json(<Object>[]);
      }),
    );

    final user = await api.login(' staff@example.com ', 'secret');
    expect(user.name, 'Saule');
    expect(api.token, 'token-123');
    expect(jsonDecode(seen.first.body), {'email': 'staff@example.com', 'password': 'secret'});

    await api.events();
    expect(seen.last.url.toString(), 'http://server:8000/api/v1/checkin/events');
    expect(seen.last.headers['Authorization'], 'Bearer token-123');
  });

  test('scan sends the exact QR text and parses the answer', () async {
    late http.Request sent;
    final api = ApiClient(
      baseUrl: 'http://server:8000',
      httpClient: MockClient((request) async {
        sent = request;
        return _json({'result': 'already_used', 'message': 'This ticket has already been used.', 'ticket': _ticket, 'stats': _stats});
      }),
    );

    final result = await api.scan('event-1', 'BFT1.ABC.DEF', checkIn: false);
    expect(sent.url.path, '/api/v1/checkin/events/event-1/scan');
    expect(jsonDecode(sent.body), {'qr_payload': 'BFT1.ABC.DEF', 'check_in': false});
    expect(result.outcome, ScanOutcome.alreadyUsed);
    expect(result.outcome.admits, isFalse);
    expect(result.ticket!.attendeeName, 'Aruzhan Bekova');
    expect(result.ticket!.checkedInAt, isNotNull);
    expect(result.stats.checkedIn, 4);
    expect(result.stats.progress, closeTo(0.4, 1e-9));
  });

  test('a Campaign QR answer never admits', () async {
    final api = ApiClient(
      baseUrl: 'http://server:8000',
      httpClient: MockClient((_) async => _json({'result': 'campaign_qr', 'message': 'Promotional code', 'ticket': null, 'stats': _stats})),
    );
    final result = await api.scan('event-1', 'https://biletflow.example/e/jazz?c=token');
    expect(result.outcome, ScanOutcome.campaignQr);
    expect(result.outcome.admits, isFalse);
    expect(result.ticket, isNull);
  });

  test('only "valid" admits, and an unknown answer is treated as invalid', () {
    expect(ScanOutcome.values.where((outcome) => outcome.admits), [ScanOutcome.valid]);
    expect(ScanOutcome.parse('something_new'), ScanOutcome.invalid);
    for (final outcome in ScanOutcome.values) {
      expect(ScanOutcome.parse(outcome.apiValue), outcome);
    }
  });

  test('server errors become ApiException with the machine code', () async {
    final api = ApiClient(
      baseUrl: 'http://server:8000',
      httpClient: MockClient((_) async => _json({'detail': 'You are not assigned to this event', 'code': 'not_event_staff'}, 403)),
    );
    await expectLater(
      api.stats('event-1'),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'not_event_staff').having((e) => e.status, 'status', 403)),
    );
  });

  test('a network failure is reported as network_error', () async {
    final api = ApiClient(baseUrl: 'http://server:8000', httpClient: MockClient((_) async => throw http.ClientException('down')));
    await expectLater(api.events(), throwsA(isA<ApiException>().having((e) => e.isNetwork, 'isNetwork', isTrue)));
  });

  test('search passes the query and parses tickets; Cyrillic survives', () async {
    late http.Request sent;
    final api = ApiClient(
      baseUrl: 'http://server:8000',
      httpClient: MockClient((request) async {
        sent = request;
        return _json([
          {..._ticket, 'attendee_name': 'Әлия Нұрланқызы', 'seat': null, 'checked_in_at': null, 'status': 'valid'},
        ]);
      }),
    );
    final found = await api.search('event-1', ' Әлия ');
    expect(sent.url.queryParameters, {'q': 'Әлия'});
    expect(found.single.attendeeName, 'Әлия Нұрланқызы');
    expect(found.single.seat, isNull);
  });
}
