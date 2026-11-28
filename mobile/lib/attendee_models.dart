
library;

DateTime _time(Object? value) => DateTime.parse(value! as String).toLocal();
DateTime? _timeOrNull(Object? value) => value == null ? null : _time(value);
List<Map<String, dynamic>> _list(Object? value) => [for (final item in (value as List<dynamic>? ?? const [])) item as Map<String, dynamic>];

/// An event in the public list.
class EventSummary {
  const EventSummary({
    required this.slug,
    required this.title,
    required this.image,
    required this.startAt,
    required this.venue,
    required this.priceFrom,
    required this.isSeated,
    required this.isCancelled,
  });

  final String slug;
  final String title;
  final String? image;
  final DateTime startAt;

  final String venue;

  /// Lowest price in tenge; 0 for a free event; null when nothing is on sale.
  final int? priceFrom;

  final bool isSeated;
  final bool isCancelled;

  factory EventSummary.fromJson(Map<String, dynamic> json) {
    final venue = json['venue'] as Map<String, dynamic>;
    final images = json['images'] as List<dynamic>;
    return EventSummary(
      slug: json['slug'] as String,
      title: json['title'] as String,
      image: images.isEmpty ? null : images.first as String,
      startAt: _time(json['start_at']),
      venue: '${venue['name']}, ${venue['city']}',
      priceFrom: json['price_from'] as int?,
      isSeated: json['seating'] == 'assigned_seating',
      isCancelled: json['event_class'] == 'cancelled',
    );
  }
}

class TicketOffer {
  const TicketOffer({required this.id, required this.name, required this.price, required this.maxPerOrder, required this.unavailableReason});

  final String id;
  final String name;
  final int price;

  final int maxPerOrder;

  /// sold_out | not_started | ended | paid_sales_inactive | event_closed; null when on sale.
  final String? unavailableReason;

  bool get onSale => unavailableReason == null;

  factory TicketOffer.fromJson(Map<String, dynamic> json) {
    final limit = json['order_limit'] as int;
    final available = json['available'] as int;
    return TicketOffer(
      id: json['id'] as String,
      name: json['name'] as String,
      price: json['price'] as int,
      maxPerOrder: available < limit ? available : limit,
      unavailableReason: (json['on_sale'] as bool) ? null : json['unavailable_reason'] as String? ?? 'event_closed',
    );
  }
}

class EventDetail {
  const EventDetail({required this.id, required this.summary, required this.address, required this.description, required this.ticketTypes});

  final String id;
  final EventSummary summary;
  final String address;
  final String? description;
  final List<TicketOffer> ticketTypes;

  factory EventDetail.fromJson(Map<String, dynamic> json) => EventDetail(
    id: json['id'] as String,
    summary: EventSummary.fromJson(json),
    address: (json['venue'] as Map<String, dynamic>)['address'] as String,
    description: json['description'] as String?,
    ticketTypes: [for (final item in _list(json['ticket_types'])) TicketOffer.fromJson(item)],
  );
}

class Selection {
  const Selection({required this.eventId, required this.quantities, this.promoCode});

  final String eventId;

  final Map<String, int> quantities;
  final String? promoCode;

  bool get isEmpty => quantities.values.every((count) => count == 0);

  Map<String, dynamic> toJson() => {
    'event_id': eventId,
    'items': [
      for (final entry in quantities.entries)
        if (entry.value > 0) {'ticket_category_id': entry.key, 'quantity': entry.value},
    ],
    'promo_code': promoCode,
  };
}

class PriceLine {
  const PriceLine({required this.name, required this.quantity, required this.amount});

  final String name;
  final int quantity;
  final int amount;

  factory PriceLine.fromJson(Map<String, dynamic> json) =>
      PriceLine(name: json['name'] as String, quantity: json['quantity'] as int, amount: json['line_total'] as int);
}

class Quote {
  const Quote({required this.lines, required this.discount, required this.total});

  final List<PriceLine> lines;
  final int discount;
  final int total;

  factory Quote.fromJson(Map<String, dynamic> json) => Quote(
    lines: [for (final item in _list(json['lines'])) PriceLine.fromJson(item)],
    discount: json['discount_total'] as int,
    total: json['total'] as int,
  );
}

class Ticket {
  const Ticket({
    required this.id,
    required this.code,
    required this.status,
    required this.ticketType,
    required this.attendeeName,
    required this.seat,
    required this.qrPayload,
    required this.eventTitle,
    required this.eventStart,
    required this.eventEnd,
    required this.venue,
  });

  final String id;
  final String code;

  /// valid | checked_in | cancelled | refunded
  final String status;
  final String ticketType;
  final String attendeeName;

  final String? seat;

  final String? qrPayload;
  final String eventTitle;
  final DateTime eventStart;
  final DateTime eventEnd;
  final String venue;

  bool get isCurrent => (status == 'valid' || status == 'checked_in') && eventEnd.isAfter(DateTime.now());

  factory Ticket.fromJson(Map<String, dynamic> json) {
    final event = json['event'] as Map<String, dynamic>;
    final seat = json['seat_number'] == null ? null : '${json['seat_section']}, ${json['seat_row']}, ${json['seat_number']}';
    return Ticket(
      id: json['id'] as String,
      code: json['code'] as String,
      status: json['status'] as String,
      ticketType: json['ticket_type'] as String,
      attendeeName: json['attendee_name'] as String,
      seat: seat,
      qrPayload: json['qr_payload'] as String?,
      eventTitle: event['title'] as String,
      eventStart: _time(event['start_at']),
      eventEnd: _time(event['end_at']),
      venue: '${event['venue_name']}, ${event['venue_city']}',
    );
  }
}

class Order {
  const Order({required this.id, required this.status, required this.total, required this.expiresAt, required this.tickets, required this.lastPaymentFailed});

  final String id;

  /// pending | completed | cancelled | refunded | expired
  final String status;
  final int total;

  final DateTime? expiresAt;
  final List<Ticket> tickets;

  final bool lastPaymentFailed;

  bool get isPending => status == 'pending';
  bool get isCompleted => status == 'completed';

  factory Order.fromJson(Map<String, dynamic> json) {
    final payments = _list(json['payments'])..sort((a, b) => (a['created_at'] as String).compareTo(b['created_at'] as String));
    return Order(
      id: json['id'] as String,
      status: json['status'] as String,
      total: json['total'] as int,
      expiresAt: _timeOrNull(json['expires_at']),
      tickets: [for (final item in _list(json['tickets'])) Ticket.fromJson(item)],
      lastPaymentFailed: payments.isNotEmpty && payments.last['status'] == 'failed',
    );
  }
}
