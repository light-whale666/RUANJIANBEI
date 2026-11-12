import 'package:dio/dio.dart';
import 'package:path/path.dart' as p;

import '../config/app_config.dart';
import '../models/json_util.dart';
import '../models/models.dart';
import 'api_exception.dart';
import 'campus_api.dart';

class RemoteCampusApi implements CampusApi {
  RemoteCampusApi({
    required this.origin,
    required this.tokenProvider,
    Dio? dio,
  }) : _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: AppConfig.apiRoot(origin),
                connectTimeout: AppConfig.connectTimeout,
                receiveTimeout: AppConfig.receiveTimeout,
                sendTimeout: AppConfig.receiveTimeout,
                headers: const {
                  'Accept': 'application/json',
                  'Content-Type': 'application/json',
                },
              ),
            ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await tokenProvider();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
  }

  final String origin;
  final Future<String?> Function() tokenProvider;
  final Dio _dio;

  Future<dynamic> _req(
    String method,
    String path, {
    Map<String, dynamic>? query,
    Object? data,
    bool optional = false,
  }) async {
    try {
      final res = await _dio.request(
        path,
        data: data,
        queryParameters: query,
        options: Options(method: method),
      );
      return res.data;
    } on DioException catch (e) {
      if (optional && (e.response?.statusCode == 404 || e.response?.statusCode == 405)) {
        return null;
      }
      throw _wrap(e);
    }
  }

  Never _wrap(DioException e) {
    final status = e.response?.statusCode;
    final data = e.response?.data;
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.connectionError) {
      throw const ApiException(
        code: 'network',
        message: '网络不可用。离线时不能回答知识问题，已缓存的待办摘要仍可查看。',
      );
    }
    if (data is Map) {
      final m = asMap(data);
      throw ApiException(
        code: asStringD(m['code'], 'error'),
        message: asStringD(m['message'], e.message ?? '请求失败'),
        details: m['details'] is Map ? asMap(m['details']) : (m['details'] != null ? {'raw': m['details']} : m),
        status: status,
      );
    }
    if (status == 401) {
      throw const ApiException(code: 'unauthorized', message: '登录已失效，请重新登录。', status: 401);
    }
    if (status == 403) {
      throw const ApiException(
        code: 'need_counselor',
        message: '该规定需辅导员查看。系统不会展示无权限正文。',
        status: 403,
      );
    }
    throw ApiException(
      code: 'http_$status',
      message: (e.message ?? '请求失败').toString(),
      status: status,
    );
  }

  Map<String, dynamic> _map(dynamic raw) {
    if (raw is Map) return asMap(raw);
    throw const ApiException(code: 'bad_response', message: '服务器返回了无法解析的数据。');
  }

  List<dynamic> _items(dynamic raw) {
    if (raw is List) return raw;
    final m = asMap(raw);
    final v = firstNonNull(m, ['items', 'data', 'results', 'todos', 'reminders', 'matches', 'approvals', 'applications', 'attachments', 'tasks']);
    if (v is List) return v;
    return const [];
  }

  @override
  Future<bool> pingHealth() async {
    try {
      final plain = Dio(BaseOptions(
        connectTimeout: const Duration(seconds: 6),
        receiveTimeout: const Duration(seconds: 6),
      ));
      final res = await plain.get(AppConfig.healthUrl(origin));
      return res.statusCode != null && res.statusCode! < 500;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<LoginResult> login(String username, String password) async {
    final raw = await _req('POST', '/auth/login', data: {
      'username': username,
      'password': password,
    });
    return LoginResult.fromJson(_map(raw));
  }

  @override
  Future<User> me() async {
    final raw = await _req('GET', '/me');
    final m = _map(raw);
    return User.fromJson(asMap(m['user']).isEmpty ? m : asMap(m['user']));
  }

  @override
  Future<Profile> getProfile() async {
    final raw = await _req('GET', '/me/profile');
    return Profile.fromJson(_map(raw));
  }

  @override
  Future<Profile> patchProfile(Map<String, dynamic> patch) async {
    final raw = await _req('PATCH', '/me/profile', data: patch);
    return Profile.fromJson(_map(raw));
  }

  @override
  Future<void> authorize({
    required String purpose,
    required List<String> fields,
    required String refType,
    String? refId,
  }) async {
    await _req('POST', '/me/authorizations', data: {
      'purpose': purpose,
      'fields': fields,
      'ref_type': refType,
      if (refId != null) 'ref_id': refId,
    });
  }

  @override
  Future<AskResult> ask({
    required String text,
    List<String> attachmentIds = const [],
    Map<String, String>? slots,
  }) async {
    final raw = await _req('POST', '/ask', data: {
      'text': text,
      if (attachmentIds.isNotEmpty) 'attachments': attachmentIds,
      if (slots != null && slots.isNotEmpty) 'slots': slots,
    });
    return AskResult.fromJson(_map(raw));
  }

  @override
  Future<AttachmentInfo> uploadAttachment(String path, {String? filename, String? kind}) async {
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(path, filename: filename ?? p.basename(path)),
      if (kind != null) 'kind': kind,
    });
    try {
      final res = await _dio.post('/attachments', data: form);
      return AttachmentInfo.fromJson(_map(res.data));
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        final res = await _dio.post('/uploads', data: form);
        return AttachmentInfo.fromJson(_map(res.data));
      }
      throw _wrap(e);
    }
  }

  @override
  Future<DocumentChunk> getChunk(String documentId, String chunkId) async {
    final raw = await _req('GET', '/documents/$documentId/chunks/$chunkId');
    return DocumentChunk.fromJson(_map(raw));
  }

  @override
  Future<List<TodoItem>> todos({String? status}) async {
    final raw = await _req('GET', '/todos', query: {
      if (status != null) 'status': status,
    });
    return _items(raw).whereType<Map>().map((e) => TodoItem.fromJson(asMap(e))).toList();
  }

  @override
  Future<ReminderBundle> reminders() async {
    final raw = await _req('GET', '/reminders');
    return ReminderBundle.fromJson(raw);
  }

  @override
  Future<void> muteReminderCategory(String cat, {bool muted = true}) async {
    await _req('POST', '/reminders/categories/$cat/mute', data: {'muted': muted});
  }

  @override
  Future<LeaveRecord> createLeave({
    String? text,
    List<String> attachmentIds = const [],
    Map<String, dynamic>? fields,
  }) async {
    final raw = await _req('POST', '/leaves', data: {
      if (text != null) 'text': text,
      if (attachmentIds.isNotEmpty) 'attachments': attachmentIds,
      if (fields != null) ...fields,
    });
    return LeaveRecord.fromJson(_map(raw));
  }

  @override
  Future<LeaveRecord> extractLeave(String id) async {
    final raw = await _req('POST', '/leaves/$id/extract');
    return LeaveRecord.fromJson(_map(raw));
  }

  @override
  Future<LeaveRecord> getLeave(String id) async {
    final raw = await _req('GET', '/leaves/$id');
    return LeaveRecord.fromJson(_map(raw));
  }

  @override
  Future<LeaveRecord> confirmLeave(String id, {Map<String, dynamic>? fields}) async {
    final raw = await _req('POST', '/leaves/$id/confirm', data: fields ?? {});
    return LeaveRecord.fromJson(_map(raw));
  }

  @override
  Future<void> withdrawLeave(String id) async {
    await _req('POST', '/leaves/$id/withdraw');
  }

  @override
  Future<LeaveRecord> returnLeave(String id, {DateTime? returnedAt}) async {
    final raw = await _req('POST', '/leaves/$id/return', data: {
      if (returnedAt != null) 'returned_at': returnedAt.toIso8601String(),
    });
    return LeaveRecord.fromJson(_map(raw));
  }

  @override
  Future<List<ApprovalItem>> approvals({String? type}) async {
    final raw = await _req('GET', '/approvals', query: {
      if (type != null) 'type': type,
    });
    return _items(raw).whereType<Map>().map((e) => ApprovalItem.fromJson(asMap(e))).toList();
  }

  @override
  Future<void> decideApproval(String id, {required String decision, String? comment}) async {
    await _req('POST', '/approvals/$id/decide', data: {
      'decision': decision,
      if (comment != null) 'comment': comment,
    });
  }

  @override
  Future<List<AidMatch>> aidMatches() async {
    final raw = await _req('GET', '/aids/matches');
    return _items(raw).whereType<Map>().map((e) => AidMatch.fromJson(asMap(e))).toList();
  }

  @override
  Future<AidDraft> createAidDraft(String programId) async {
    final raw = await _req('POST', '/aids/$programId/draft');
    return AidDraft.fromJson(_map(raw));
  }

  @override
  Future<AidDraft> getAidDraft(String id) async {
    final raw = await _req('GET', '/aids/drafts/$id', optional: true);
    if (raw == null) {
      throw const ApiException(code: 'not_found', message: '未找到该奖助草稿。', status: 404);
    }
    return AidDraft.fromJson(_map(raw));
  }

  @override
  Future<AidDraft> confirmAidDraft(String id, {Map<String, dynamic>? fields}) async {
    final raw = await _req('POST', '/aids/drafts/$id/confirm', data: fields ?? {});
    return AidDraft.fromJson(_map(raw));
  }

  @override
  Future<TaskItem> getTask(String id) async {
    final raw = await _req('GET', '/tasks/$id');
    return TaskItem.fromJson(_map(raw));
  }

  @override
  Future<TaskItem> submitTask(
    String id, {
    String? note,
    List<String> attachmentIds = const [],
    Map<String, dynamic>? fields,
  }) async {
    final raw = await _req('POST', '/tasks/$id/submit', data: {
      if (note != null) 'note': note,
      if (attachmentIds.isNotEmpty) 'attachments': attachmentIds,
      if (fields != null) ...fields,
    });
    return TaskItem.fromJson(_map(raw));
  }

  @override
  Future<TaskItem> createTask({
    required String type,
    required String title,
    String? body,
    DateTime? dueAt,
    String? audience,
    Map<String, dynamic>? extra,
  }) async {
    final raw = await _req('POST', '/tasks', data: {
      'type': type,
      'title': title,
      if (body != null) 'body': body,
      if (dueAt != null) 'due_at': dueAt.toIso8601String(),
      if (audience != null) 'audience': audience,
      if (extra != null) ...extra,
    });
    return TaskItem.fromJson(_map(raw));
  }

  @override
  Future<TaskProgress> taskProgress(String id) async {
    final raw = await _req('GET', '/tasks/$id/progress');
    return TaskProgress.fromJson(_map(raw));
  }

  @override
  Future<List<ApplicationItem>> myApplications() async {
    final raw = await _req('GET', '/me/applications', optional: true);
    if (raw != null) {
      return _items(raw).whereType<Map>().map((e) => ApplicationItem.fromJson(asMap(e))).toList();
    }
    final leaves = await _req('GET', '/leaves', optional: true);
    final drafts = await _req('GET', '/aids/drafts', optional: true);
    final items = <ApplicationItem>[];
    for (final e in _items(leaves)) {
      if (e is Map) {
        final m = asMap(e);
        items.add(ApplicationItem.fromJson({
          ...m,
          'kind': 'leave',
          'title': m['title'] ?? m['reason'] ?? '请假',
        }));
      }
    }
    for (final e in _items(drafts)) {
      if (e is Map) {
        final m = asMap(e);
        items.add(ApplicationItem.fromJson({
          ...m,
          'kind': 'aid',
          'title': m['title'] ?? '奖助草稿',
        }));
      }
    }
    return items;
  }

  @override
  Future<List<AttachmentInfo>> myAttachments() async {
    final raw = await _req('GET', '/me/attachments', optional: true);
    if (raw == null) return const [];
    return _items(raw).whereType<Map>().map((e) => AttachmentInfo.fromJson(asMap(e))).toList();
  }
}
