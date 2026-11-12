import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// 非密钥本地存储：服务器地址、用户摘要、待办/会话摘要缓存。
class LocalStore {
  LocalStore(this._prefs);

  final SharedPreferences _prefs;

  static const originKey = 'api_base_url';
  static const userKey = 'cached_user';
  static const todosKey = 'cached_todos_summary';
  static const convKey = 'cached_conversations';

  String? get origin => _prefs.getString(originKey);

  Future<void> setOrigin(String origin) => _prefs.setString(originKey, origin);

  Map<String, dynamic>? get userJson {
    final s = _prefs.getString(userKey);
    if (s == null || s.isEmpty) return null;
    try {
      return jsonDecode(s) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<void> setUserJson(Map<String, dynamic>? json) async {
    if (json == null) {
      await _prefs.remove(userKey);
    } else {
      await _prefs.setString(userKey, jsonEncode(json));
    }
  }

  Future<void> cacheTodoSummary(String json) => _prefs.setString(todosKey, json);

  String? get todoSummary => _prefs.getString(todosKey);

  /// 只缓存会话摘要（结论短句 + 时间），不缓存规章全文。
  List<Map<String, dynamic>> conversationSummaries() {
    final s = _prefs.getString(convKey);
    if (s == null) return const [];
    try {
      final list = jsonDecode(s) as List;
      return list.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    } catch (_) {
      return const [];
    }
  }

  Future<void> addConversationSummary({
    required String id,
    required String question,
    required String conclusion,
  }) async {
    final items = conversationSummaries();
    items.insert(0, {
      'id': id,
      'question': question,
      'conclusion': conclusion,
      'at': DateTime.now().toIso8601String(),
    });
    final trimmed = items.take(20).toList();
    await _prefs.setString(convKey, jsonEncode(trimmed));
  }

  Future<void> clearSessionCache() async {
    await _prefs.remove(userKey);
    await _prefs.remove(todosKey);
    await _prefs.remove(convKey);
  }
}
