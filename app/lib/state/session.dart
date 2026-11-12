import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';
import '../demo/demo_api.dart';
import '../models/models.dart';
import '../services/api_exception.dart';
import '../services/campus_api.dart';
import '../services/local_store.dart';
import '../services/remote_api.dart';
import '../services/token_store.dart';

class Session extends ChangeNotifier {
  Session({TokenStore? tokens}) : _tokens = tokens ?? TokenStore();

  final TokenStore _tokens;
  late LocalStore _local;

  bool ready = false;
  bool demoMode = false;
  String? demoRoleKey;
  String origin = AppConfig.defaultOrigin;
  User? user;
  bool online = true;
  String? lastError;

  CampusApi api = RemoteCampusApi(
    origin: AppConfig.defaultOrigin,
    tokenProvider: () async => null,
  );

  String? _token;

  bool get loggedIn => user != null;
  bool get isStudent => user?.role == UserRole.student;
  bool get isTeacher => user?.role == UserRole.teacher;
  bool get isCounselor => user?.role == UserRole.counselor;
  bool get isStaff => user?.isStaff == true;

  Future<void> bootstrap() async {
    final prefs = await SharedPreferences.getInstance();
    _local = LocalStore(prefs);
    origin = AppConfig.normalizeOrigin(_local.origin ?? AppConfig.defaultOrigin);
    _token = await _tokens.read();
    final cached = _local.userJson;
    if (cached != null) {
      try {
        user = User.fromJson(cached);
      } catch (_) {}
    }
    _rebuildApi();
    if (_token != null && _token!.isNotEmpty && !demoMode) {
      try {
        user = await api.me();
        await _local.setUserJson(user!.toJson());
        online = true;
      } on ApiException catch (e) {
        online = !e.isOffline;
        if (e.isUnauthorized) {
          await logout(keepOrigin: true);
        }
      } catch (_) {
        online = false;
      }
    }
    ready = true;
    notifyListeners();
  }

  void _rebuildApi() {
    if (demoMode) {
      api = DemoCampusApi(roleKey: demoRoleKey ?? 'freshman');
    } else {
      api = RemoteCampusApi(
        origin: origin,
        tokenProvider: () async => _token,
      );
    }
  }

  Future<void> setOrigin(String value) async {
    origin = AppConfig.normalizeOrigin(value);
    await _local.setOrigin(origin);
    if (!demoMode) _rebuildApi();
    notifyListeners();
  }

  Future<bool> checkHealth() async {
    if (demoMode) {
      online = true;
      notifyListeners();
      return true;
    }
    final ok = await RemoteCampusApi(
      origin: origin,
      tokenProvider: () async => _token,
    ).pingHealth();
    online = ok;
    notifyListeners();
    return ok;
  }

  Future<void> login(String username, String password) async {
    demoMode = false;
    demoRoleKey = null;
    _rebuildApi();
    final result = await api.login(username, password);
    _token = result.accessToken;
    await _tokens.save(result.accessToken);
    user = result.user;
    await _local.setUserJson(user!.toJson());
    online = true;
    lastError = null;
    notifyListeners();
  }

  Future<void> enterDemo(String roleKey) async {
    await _tokens.clear();
    _token = null;
    demoMode = true;
    demoRoleKey = roleKey;
    _rebuildApi();
    user = await api.me();
    await _local.setUserJson(user!.toJson());
    online = true;
    notifyListeners();
  }

  Future<void> logout({bool keepOrigin = true}) async {
    await _tokens.clear();
    _token = null;
    user = null;
    demoMode = false;
    demoRoleKey = null;
    await _local.clearSessionCache();
    _rebuildApi();
    notifyListeners();
  }

  Future<T> guard<T>(Future<T> Function() run) async {
    try {
      final v = await run();
      lastError = null;
      return v;
    } on ApiException catch (e) {
      lastError = e.message;
      if (e.isOffline) online = false;
      if (e.isUnauthorized && !demoMode) {
        await logout(keepOrigin: true);
      }
      rethrow;
    }
  }

  Future<void> cacheTodos(List<TodoItem> items) async {
    final summary = items
        .map((e) => {'id': e.id, 'title': e.title, 'due_at': e.dueAt?.toIso8601String(), 'type': e.type})
        .toList();
    await _local.cacheTodoSummary(jsonEncode(summary));
  }

  List<Map<String, dynamic>> cachedTodoSummary() {
    final raw = _local.todoSummary;
    if (raw == null) return const [];
    try {
      return (jsonDecode(raw) as List).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    } catch (_) {
      return const [];
    }
  }

  Future<void> rememberConversation({
    required String id,
    required String question,
    required String conclusion,
  }) {
    return _local.addConversationSummary(id: id, question: question, conclusion: conclusion);
  }

  List<Map<String, dynamic>> conversationSummaries() => _local.conversationSummaries();
}
