/// HTTP client for the BiletFlow API: the calls the attendee screens and the check-in screens need.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'attendee_models.dart';
import 'models.dart';

class ApiException implements Exception {
  const ApiException(this.status, this.code, this.detail);

  final int status;
  final String code;
  final String detail;

  bool get isNetwork => code == 'network_error';
  bool get isUnauthorized => status == 401;

  @override
  String toString() => 'ApiException($status, $code): $detail';
}

class ApiClient {
  ApiClient({required String baseUrl, http.Client? httpClient, this.token})
    : baseUrl = normalizeBaseUrl(baseUrl),
      _http = httpClient ?? http.Client();

  /// Server address without a trailing slash, for example http://192.168.1.20:8000
  String baseUrl;

  /// Access token of the signed-in user (null before sign-in).
  String? token;
  final http.Client _http;

  static const _timeout = Duration(seconds: 10);

  static String normalizeBaseUrl(String value) {
    var url = value.trim();
    while (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }
    return url;
  }

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('$baseUrl/api/v1$path').replace(queryParameters: (query == null || query.isEmpty) ? null : query);

  Future<dynamic> _send(String method, String path, {Object? body, Map<String, String>? query}) async {
    final headers = <String, String>{'Accept': 'application/json'};
    if (token != null) headers['Authorization'] = 'Bearer $token';
    if (body != null) headers['Content-Type'] = 'application/json';

    http.Response response;
    try {
      final request = http.Request(method, _uri(path, query))..headers.addAll(headers);
      if (body != null) request.body = jsonEncode(body);
      response = await http.Response.fromStream(await _http.send(request).timeout(_timeout));
    } on TimeoutException {
      throw const ApiException(0, 'network_error', 'The server did not answer in time');
    } on SocketException {
      throw const ApiException(0, 'network_error', 'The server cannot be reached');
    } on http.ClientException {
      throw const ApiException(0, 'network_error', 'The server cannot be reached');
    }

    final text = utf8.decode(response.bodyBytes);
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return text.isEmpty ? null : jsonDecode(text);
    }
    var code = 'error';
    var detail = 'Request failed (${response.statusCode})';
    try {
      final json = jsonDecode(text) as Map<String, dynamic>;
      code = (json['code'] as String?) ?? code;
      if (json['detail'] is String) detail = json['detail'] as String;
    } on Object {
    }
    throw ApiException(response.statusCode, code, detail);
  }

  //  account 

  Future<AppUser> login(String email, String password) async {
    final json = await _send('POST', '/auth/login', body: {'email': email.trim(), 'password': password}) as Map<String, dynamic>;
    token = json['access_token'] as String;
    return AppUser.fromJson(json['user'] as Map<String, dynamic>);
  }

  Future<AppUser> me() async => AppUser.fromJson(await _send('GET', '/auth/me') as Map<String, dynamic>);

  Future<void> register({required String name, required String email, required String password, required String language}) => _send(
    'POST',
    '/auth/register',
    body: {'name': name.trim(), 'email': email.trim(), 'password': password, 'role': 'attendee', 'locale': language},
  );

  Future<List<EventSummary>> listEvents({String query = ''}) async {
    final json = await _send('GET', '/events', query: {if (query.trim().isNotEmpty) 'q': query.trim(), 'limit': '50'}) as Map<String, dynamic>;
    return [for (final item in json['items'] as List<dynamic>) EventSummary.fromJson(item as Map<String, dynamic>)];
  }

  Future<EventDetail> event(String slug) async => EventDetail.fromJson(await _send('GET', '/events/$slug') as Map<String, dynamic>);
  Future<Quote> quote(Selection selection) async =>
      Quote.fromJson(await _send('POST', '/orders/quote', body: selection.toJson()) as Map<String, dynamic>);
  Future<Order> createOrder(Selection selection, {required String name, required String email, String phone = ''}) async =>
      Order.fromJson(
        await _send('POST', '/orders', body: {
          ...selection.toJson(),
          'buyer_name': name.trim(),
          'buyer_email': email.trim(),
          'buyer_phone': phone.trim().isEmpty ? null : phone.trim(),
        }) as Map<String, dynamic>,
      );

  Future<Order> order(String id) async => Order.fromJson(await _send('GET', '/orders/$id') as Map<String, dynamic>);
  Future<Order> pay(String orderId, {required bool succeed}) async => Order.fromJson(
    await _send('POST', '/orders/$orderId/pay', body: {'outcome': succeed ? 'success' : 'failure'}) as Map<String, dynamic>,
  );
  Future<List<Ticket>> myTickets() async {
    final list = await _send('GET', '/tickets') as List<dynamic>;
    return [for (final item in list) Ticket.fromJson(item as Map<String, dynamic>)];
  }

  // - check-in 

  Future<List<StaffEvent>> events() async {
    final list = await _send('GET', '/checkin/events') as List<dynamic>;
    return [for (final item in list) StaffEvent.fromJson(item as Map<String, dynamic>)];
  }

  Future<CheckInStats> stats(String eventId) async =>
      CheckInStats.fromJson(await _send('GET', '/checkin/events/$eventId/stats') as Map<String, dynamic>);

  Future<ScanResult> scan(String eventId, String qrPayload, {bool checkIn = true}) async => ScanResult.fromJson(
    await _send('POST', '/checkin/events/$eventId/scan', body: {'qr_payload': qrPayload, 'check_in': checkIn})
        as Map<String, dynamic>,
  );

  /// Manual search by name, email, ticket code or order number.
  Future<List<TicketInfo>> search(String eventId, String query) async {
    final list = await _send('GET', '/checkin/events/$eventId/attendees', query: {'q': query.trim()}) as List<dynamic>;
    return [for (final item in list) TicketInfo.fromJson(item as Map<String, dynamic>)];
  }

  Future<ScanResult> manualCheckIn(String eventId, String ticketId) async => ScanResult.fromJson(
    await _send('POST', '/checkin/events/$eventId/tickets/$ticketId/check-in') as Map<String, dynamic>,
  );

  Future<ScanResult> undoCheckIn(String eventId, String ticketId) async =>
      ScanResult.fromJson(await _send('POST', '/checkin/events/$eventId/tickets/$ticketId/undo') as Map<String, dynamic>);

  Future<List<ActivityRecord>> recent(String eventId) async {
    final list = await _send('GET', '/checkin/events/$eventId/recent') as List<dynamic>;
    return [for (final item in list) ActivityRecord.fromJson(item as Map<String, dynamic>)];
  }
}
