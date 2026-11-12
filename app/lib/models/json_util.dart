String? asString(dynamic v) {
  if (v == null) return null;
  if (v is String) return v.trim().isEmpty ? null : v;
  final s = v.toString();
  return s.trim().isEmpty ? null : s;
}

String asStringD(dynamic v, [String fallback = '']) => asString(v) ?? fallback;

int? asInt(dynamic v) {
  if (v == null) return null;
  if (v is int) return v;
  if (v is num) return v.toInt();
  return int.tryParse(v.toString());
}

bool asBool(dynamic v, [bool fallback = false]) {
  if (v == null) return fallback;
  if (v is bool) return v;
  if (v is num) return v != 0;
  final s = v.toString().toLowerCase();
  if (s == 'true' || s == '1' || s == 'yes') return true;
  if (s == 'false' || s == '0' || s == 'no') return false;
  return fallback;
}

DateTime? asDate(dynamic v) {
  if (v == null) return null;
  if (v is DateTime) return v;
  if (v is int) {
    if (v > 100000000000) {
      return DateTime.fromMillisecondsSinceEpoch(v);
    }
    if (v > 1000000000) {
      return DateTime.fromMillisecondsSinceEpoch(v * 1000);
    }
  }
  return DateTime.tryParse(v.toString());
}

Map<String, dynamic> asMap(dynamic v) {
  if (v is Map<String, dynamic>) return v;
  if (v is Map) {
    return v.map((k, val) => MapEntry(k.toString(), val));
  }
  return <String, dynamic>{};
}

List<dynamic> asList(dynamic v) {
  if (v is List) return v;
  return const [];
}

T? asObj<T>(dynamic v, T Function(Map<String, dynamic>) parse) {
  if (v is Map) return parse(asMap(v));
  return null;
}

List<T> asObjList<T>(dynamic v, T Function(Map<String, dynamic>) parse) {
  return asList(v)
      .whereType<Map>()
      .map((e) => parse(asMap(e)))
      .toList();
}

dynamic firstNonNull(Map<String, dynamic> m, List<String> keys) {
  for (final k in keys) {
    if (m.containsKey(k) && m[k] != null) return m[k];
  }
  return null;
}
