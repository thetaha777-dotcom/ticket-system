library;

class AppUser {
  const AppUser({required this.id, required this.name, required this.email, required this.role});

  final String id;
  final String name;
  final String email;
  final String role;

  bool get worksAtEvents => role == 'event_admin' || role == 'organizer' || role == 'platform_admin';

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
    id: json['id'] as String,
    name: json['name'] as String,
    email: json['email'] as String,
    role: json['role'] as String,
  );
}

class CheckInStats {
  const CheckInStats({required this.registered, required this.checkedIn, required this.remaining});

  final int registered;
  final int checkedIn;
  final int remaining;

  double get progress => registered == 0 ? 0 : checkedIn / registered;

  factory CheckInStats.fromJson(Map<String, dynamic> json) => CheckInStats(
    registered: json['registered'] as int,
    checkedIn: json['checked_in'] as int,
    remaining: json['remaining'] as int,
  );
}

class StaffEvent {
  const StaffEvent({
    required this.id,
    required this.title,
    required this.startAt,
    required this.endAt,
    required this.eventClass,
    required this.venueName,
    required this.venueCity,
    required this.canUndo,
    required this.stats,
  });

  final String id;
  final String title;
  final DateTime startAt;
  final DateTime endAt;

  /// upcoming | active
  final String eventClass;
  final String venueName;
  final String venueCity;

  final bool canUndo;
  final CheckInStats stats;

  factory StaffEvent.fromJson(Map<String, dynamic> json) => StaffEvent(
    id: json['id'] as String,
    title: json['title'] as String,
    startAt: DateTime.parse(json['start_at'] as String).toLocal(),
    endAt: DateTime.parse(json['end_at'] as String).toLocal(),
    eventClass: json['event_class'] as String,
    venueName: json['venue_name'] as String,
    venueCity: json['venue_city'] as String,
    canUndo: json['can_undo'] as bool,
    stats: CheckInStats.fromJson(json['stats'] as Map<String, dynamic>),
  );
}

class TicketInfo {
  const TicketInfo({
    required this.id,
    required this.code,
    required this.status,
    required this.attendeeName,
    required this.attendeeEmail,
    required this.ticketType,
    required this.orderNumber,
    this.seat,
    this.checkedInAt,
  });

  final String id;
  final String code;

  /// valid | checked_in | cancelled | refunded
  final String status;
  final String attendeeName;
  final String attendeeEmail;
  final String ticketType;
  final String orderNumber;
  final String? seat;
  final DateTime? checkedInAt;

  factory TicketInfo.fromJson(Map<String, dynamic> json) => TicketInfo(
    id: json['id'] as String,
    code: json['code'] as String,
    status: json['status'] as String,
    attendeeName: json['attendee_name'] as String,
    attendeeEmail: json['attendee_email'] as String,
    ticketType: json['ticket_type'] as String,
    orderNumber: json['order_number'] as String,
    seat: json['seat'] as String?,
    checkedInAt: json['checked_in_at'] == null ? null : DateTime.parse(json['checked_in_at'] as String).toLocal(),
  );
}

enum ScanOutcome {
  valid('valid'),
  alreadyUsed('already_used'),
  cancelled('cancelled'),
  refunded('refunded'),
  invalid('invalid'),
  wrongEvent('wrong_event'),

  campaignQr('campaign_qr');

  const ScanOutcome(this.apiValue);
  final String apiValue;

  static ScanOutcome parse(String value) =>
      ScanOutcome.values.firstWhere((outcome) => outcome.apiValue == value, orElse: () => ScanOutcome.invalid);

  bool get admits => this == ScanOutcome.valid;
}

class ScanResult {
  const ScanResult({required this.outcome, required this.message, required this.stats, this.ticket});

  final ScanOutcome outcome;

  final String message;
  final TicketInfo? ticket;
  final CheckInStats stats;

  factory ScanResult.fromJson(Map<String, dynamic> json) => ScanResult(
    outcome: ScanOutcome.parse(json['result'] as String),
    message: json['message'] as String,
    ticket: json['ticket'] == null ? null : TicketInfo.fromJson(json['ticket'] as Map<String, dynamic>),
    stats: CheckInStats.fromJson(json['stats'] as Map<String, dynamic>),
  );
}

class ActivityRecord {
  const ActivityRecord({
    required this.id,
    required this.action,
    required this.method,
    required this.createdAt,
    required this.staffName,
    required this.ticketCode,
    required this.attendeeName,
  });

  final String id;

  final String action;

  final String method;
  final DateTime createdAt;
  final String staffName;
  final String ticketCode;
  final String attendeeName;

  factory ActivityRecord.fromJson(Map<String, dynamic> json) => ActivityRecord(
    id: json['id'] as String,
    action: json['action'] as String,
    method: json['method'] as String,
    createdAt: DateTime.parse(json['created_at'] as String).toLocal(),
    staffName: json['staff_name'] as String,
    ticketCode: json['ticket_code'] as String,
    attendeeName: json['attendee_name'] as String,
  );
}
