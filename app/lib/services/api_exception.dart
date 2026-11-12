class ApiException implements Exception {
  const ApiException({
    required this.code,
    required this.message,
    this.details,
    this.status,
  });

  final String code;
  final String message;
  final Map<String, dynamic>? details;
  final int? status;

  bool get isUnauthorized => status == 401 || code == 'unauthorized';
  bool get isForbidden => status == 403 || code == 'need_counselor' || code == 'forbidden';
  bool get isValidationBlocked => code == 'validation_blocked';
  bool get needCounselor => code == 'need_counselor';
  bool get isOffline => code == 'offline' || code == 'network';

  List<String> get missingMessages {
    final raw = details?['missing'];
    if (raw is! List) return const [];
    return raw.map((e) {
      if (e is Map) {
        return (e['message'] ?? e['reason'] ?? e['field'] ?? '').toString();
      }
      return e.toString();
    }).where((s) => s.isNotEmpty).toList();
  }

  @override
  String toString() => message;
}
