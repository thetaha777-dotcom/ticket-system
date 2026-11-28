/// Formatting of money and dates, the same way in every screen.
library;

import 'package:intl/intl.dart';

/// "12 500 ₸". Amounts from the API are whole tenge; the spaces are non-breaking.
String money(int amount) => '${NumberFormat.decimalPattern('ru').format(amount).replaceAll(RegExp(r'\s'), ' ')} ₸';

/// "12 December 2026, 19:00" in the interface language.
String dateTime(DateTime value, String language) => DateFormat('d MMMM y, HH:mm', language).format(value);

/// "Sat, 12 Dec, 19:00" for lists.
String shortDateTime(DateTime value, String language) => DateFormat('EEE, d MMM, HH:mm', language).format(value);

/// "09:41" for the reservation countdown.
String countdown(Duration left) {
  final seconds = left.isNegative ? 0 : left.inSeconds;
  return '${(seconds ~/ 60).toString().padLeft(2, '0')}:${(seconds % 60).toString().padLeft(2, '0')}';
}
