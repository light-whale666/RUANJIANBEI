import 'json_util.dart';

enum UserRole { student, teacher, counselor, admin, unknown }

UserRole roleFrom(dynamic v) {
  switch ((v ?? '').toString().toLowerCase()) {
    case 'student':
      return UserRole.student;
    case 'teacher':
      return UserRole.teacher;
    case 'counselor':
    case 'advisor':
    case 'headteacher':
    case 'head_teacher':
    case '班主任':
    case '辅导员':
      return UserRole.counselor;
    case 'admin':
      return UserRole.admin;
    default:
      return UserRole.unknown;
  }
}

String roleLabel(UserRole role) {
  switch (role) {
    case UserRole.student:
      return '学生';
    case UserRole.teacher:
      return '任课教师';
    case UserRole.counselor:
      return '辅导员';
    case UserRole.admin:
      return '管理员';
    case UserRole.unknown:
      return '用户';
  }
}

class User {
  const User({
    required this.id,
    required this.username,
    required this.name,
    required this.role,
    this.isFreshman = false,
    this.college,
    this.className,
    this.studentNo,
    this.staffNo,
  });

  final String id;
  final String username;
  final String name;
  final UserRole role;
  final bool isFreshman;
  final String? college;
  final String? className;
  final String? studentNo;
  final String? staffNo;

  bool get isStaff =>
      role == UserRole.teacher || role == UserRole.counselor;

  factory User.fromJson(Map<String, dynamic> j) {
    final role = roleFrom(firstNonNull(j, ['role', 'user_role']));
    final grade = asString(firstNonNull(j, ['grade', 'year', '年级']));
    final isFreshman = asBool(firstNonNull(j, ['is_freshman', 'freshman'])) ||
        (grade != null &&
            (grade.contains('新生') ||
                grade.contains('2026') ||
                grade.contains('一年级') ||
                grade.toLowerCase() == 'freshman'));
    return User(
      id: asStringD(firstNonNull(j, ['id', 'user_id', 'uid'])),
      username: asStringD(firstNonNull(j, ['username', 'login', 'account'])),
      name: asStringD(firstNonNull(j, ['name', 'display_name', 'real_name']), '同学'),
      role: role,
      isFreshman: isFreshman,
      college: asString(firstNonNull(j, ['college', 'school', 'faculty'])),
      className: asString(firstNonNull(j, ['class_name', 'className', 'klass', 'class'])),
      studentNo: asString(firstNonNull(j, ['student_no', 'studentNo', 'stu_id'])),
      staffNo: asString(firstNonNull(j, ['staff_no', 'staffNo', 'employee_no'])),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'name': name,
        'role': role.name,
        'is_freshman': isFreshman,
        'college': college,
        'class_name': className,
        'student_no': studentNo,
        'staff_no': staffNo,
      };
}

class LoginResult {
  const LoginResult({
    required this.accessToken,
    required this.tokenType,
    required this.role,
    required this.user,
  });

  final String accessToken;
  final String tokenType;
  final UserRole role;
  final User user;

  factory LoginResult.fromJson(Map<String, dynamic> j) {
    final userMap = asMap(j['user']);
    final role = roleFrom(firstNonNull(j, ['role']) ?? userMap['role']);
    final user = userMap.isEmpty
        ? User(
            id: asStringD(j['user_id']),
            username: asStringD(j['username']),
            name: asStringD(j['name'], '同学'),
            role: role,
          )
        : User.fromJson({...userMap, 'role': userMap['role'] ?? role.name});
    return LoginResult(
      accessToken: asStringD(firstNonNull(j, ['access_token', 'token'])),
      tokenType: asStringD(j['token_type'], 'bearer'),
      role: role == UserRole.unknown ? user.role : role,
      user: user,
    );
  }
}

class EmergencyContact {
  const EmergencyContact({
    required this.name,
    required this.relation,
    required this.phone,
  });

  final String name;
  final String relation;
  final String phone;

  factory EmergencyContact.fromJson(Map<String, dynamic> j) => EmergencyContact(
        name: asStringD(j['name']),
        relation: asStringD(firstNonNull(j, ['relation', 'relationship'])),
        phone: asStringD(firstNonNull(j, ['phone', 'mobile', 'tel'])),
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'relation': relation,
        'phone': phone,
      };
}

class Profile {
  const Profile({
    this.studentNo,
    this.staffNo,
    required this.name,
    this.college,
    this.major,
    this.grade,
    this.className,
    this.phone,
    this.email,
    this.counselorName,
    this.counselorId,
    this.dorm,
    this.bed,
    this.emergencyContacts = const [],
    this.authorizedFields = const {},
  });

  final String? studentNo;
  final String? staffNo;
  final String name;
  final String? college;
  final String? major;
  final String? grade;
  final String? className;
  final String? phone;
  final String? email;
  final String? counselorName;
  final String? counselorId;
  final String? dorm;
  final String? bed;
  final List<EmergencyContact> emergencyContacts;
  final Set<String> authorizedFields;

  factory Profile.fromJson(Map<String, dynamic> j) {
    final contacts = firstNonNull(j, ['emergency_contacts', 'emergencyContacts']) ??
        (j['emergency_name'] != null
            ? [
                {
                  'name': j['emergency_name'],
                  'relation': j['emergency_relation'],
                  'phone': j['emergency_phone'],
                }
              ]
            : []);
    final auth = firstNonNull(j, ['authorized_fields', 'authorizations']) ?? [];
    final fields = <String>{};
    for (final item in asList(auth)) {
      if (item is String) fields.add(item);
      if (item is Map) {
        fields.addAll(asList(item['fields']).map((e) => e.toString()));
      }
    }
    return Profile(
      studentNo: asString(firstNonNull(j, ['student_no', 'studentNo', 'stu_id'])),
      staffNo: asString(firstNonNull(j, ['staff_no', 'staffNo', 'employee_no'])),
      name: asStringD(j['name']),
      college: asString(firstNonNull(j, ['college', 'school'])),
      major: asString(firstNonNull(j, ['major', 'specialty'])),
      grade: asString(firstNonNull(j, ['grade', 'year'])),
      className: asString(firstNonNull(j, ['class_name', 'className', 'klass', 'class'])),
      phone: asString(firstNonNull(j, ['phone', 'mobile'])),
      email: asString(j['email']),
      counselorName: asString(firstNonNull(j, ['counselor', 'counselor_name'])),
      counselorId: asString(j['counselor_id']),
      dorm: asString(firstNonNull(j, ['dorm', 'dormitory', 'room'])),
      bed: asString(firstNonNull(j, ['bed', 'bed_no'])),
      emergencyContacts: asObjList(contacts, EmergencyContact.fromJson),
      authorizedFields: fields,
    );
  }

  Profile copyWith({
    String? phone,
    String? email,
    String? dorm,
    String? bed,
    List<EmergencyContact>? emergencyContacts,
    Set<String>? authorizedFields,
  }) {
    return Profile(
      studentNo: studentNo,
      staffNo: staffNo,
      name: name,
      college: college,
      major: major,
      grade: grade,
      className: className,
      phone: phone ?? this.phone,
      email: email ?? this.email,
      counselorName: counselorName,
      counselorId: counselorId,
      dorm: dorm ?? this.dorm,
      bed: bed ?? this.bed,
      emergencyContacts: emergencyContacts ?? this.emergencyContacts,
      authorizedFields: authorizedFields ?? this.authorizedFields,
    );
  }
}

class Citation {
  const Citation({
    required this.documentId,
    required this.chunkId,
    required this.filename,
    this.section,
    this.article,
    this.semester,
    this.quote = '',
    this.isGoverning = false,
  });

  final String documentId;
  final String chunkId;
  final String filename;
  final String? section;
  final String? article;
  final String? semester;
  final String quote;
  final bool isGoverning;

  String get clause {
    final parts = [section, article].whereType<String>().where((s) => s.isNotEmpty);
    return parts.join(' ');
  }

  String get subtitle {
    final bits = <String>[];
    if (clause.isNotEmpty) bits.add(clause);
    if (semester != null && semester!.isNotEmpty) bits.add(semester!);
    return bits.join(' · ');
  }

  factory Citation.fromJson(Map<String, dynamic> j) => Citation(
        documentId: asStringD(firstNonNull(j, ['document_id', 'documentId', 'doc_id'])),
        chunkId: asStringD(firstNonNull(j, ['chunk_id', 'chunkId'])),
        filename: asStringD(firstNonNull(j, ['filename', 'title', 'document_name'])),
        section: asString(firstNonNull(j, ['section', 'chapter'])),
        article: asString(firstNonNull(j, ['article', 'clause'])),
        semester: asString(firstNonNull(j, ['semester', 'effective_semester'])),
        quote: asStringD(firstNonNull(j, ['quote', 'text', 'snippet'])),
        isGoverning: asBool(firstNonNull(j, ['is_governing', 'governing', 'preferred'])),
      );
}

class ConflictNote {
  const ConflictNote({
    required this.chosen,
    required this.other,
    required this.reason,
  });

  final String chosen;
  final String other;
  final String reason;

  factory ConflictNote.fromJson(Map<String, dynamic> j) => ConflictNote(
        chosen: asStringD(firstNonNull(j, ['chosen', 'governing', 'preferred'])),
        other: asStringD(firstNonNull(j, ['other', 'superseded'])),
        reason: asStringD(j['reason']),
      );
}

class AnswerAction {
  const AnswerAction({
    required this.type,
    required this.label,
    this.ref = const {},
  });

  final String type;
  final String label;
  final Map<String, dynamic> ref;

  String? get refId =>
      asString(firstNonNull(ref, ['id', 'ref_id', 'leave_id', 'task_id', 'program_id', 'draft_id']));

  factory AnswerAction.fromJson(Map<String, dynamic> j) => AnswerAction(
        type: asStringD(j['type']),
        label: asStringD(j['label'], '去办理'),
        ref: j['ref'] is Map ? asMap(j['ref']) : (j['ref'] != null ? {'id': j['ref']} : {}),
      );
}

class HumanEntry {
  const HumanEntry({required this.type, required this.label});

  final String type;
  final String label;

  factory HumanEntry.fromJson(Map<String, dynamic> j) => HumanEntry(
        type: asStringD(j['type'], 'counselor'),
        label: asStringD(j['label'], '转给辅导员'),
      );
}

class SlotNeed {
  const SlotNeed({required this.field, required this.question});

  final String field;
  final String question;

  factory SlotNeed.fromJson(Map<String, dynamic> j) => SlotNeed(
        field: asStringD(firstNonNull(j, ['field', 'name', 'key'])),
        question: asStringD(firstNonNull(j, ['question', 'label', 'prompt'])),
      );
}

class AskResult {
  const AskResult({
    required this.conversationId,
    this.intent,
    required this.conclusion,
    this.citations = const [],
    this.conflicts = const [],
    this.action,
    this.humanEntry,
    this.permissionDenied = false,
    this.slotsNeeded = const [],
  });

  final String conversationId;
  final String? intent;
  final String conclusion;
  final List<Citation> citations;
  final List<ConflictNote> conflicts;
  final AnswerAction? action;
  final HumanEntry? humanEntry;
  final bool permissionDenied;
  final List<SlotNeed> slotsNeeded;

  factory AskResult.fromJson(Map<String, dynamic> j) {
    final answer = asMap(firstNonNull(j, ['answer']) ?? j);
    return AskResult(
      conversationId: asStringD(firstNonNull(j, ['conversation_id', 'id'])),
      intent: asString(j['intent']),
      conclusion: asStringD(answer['conclusion']),
      citations: asObjList(answer['citations'] ?? j['citations'], Citation.fromJson),
      conflicts: asObjList(answer['conflicts'] ?? j['conflicts'], ConflictNote.fromJson),
      action: asObj(answer['action'], AnswerAction.fromJson),
      humanEntry: asObj(answer['human_entry'] ?? answer['humanEntry'], HumanEntry.fromJson),
      permissionDenied: asBool(answer['permission_denied']),
      slotsNeeded: asObjList(j['slots_needed'] ?? answer['slots_needed'], SlotNeed.fromJson),
    );
  }
}

class DocumentChunk {
  const DocumentChunk({
    required this.documentId,
    required this.chunkId,
    required this.filename,
    this.section,
    this.article,
    this.semester,
    required this.text,
    this.highlight,
  });

  final String documentId;
  final String chunkId;
  final String filename;
  final String? section;
  final String? article;
  final String? semester;
  final String text;
  final String? highlight;

  factory DocumentChunk.fromJson(Map<String, dynamic> j) => DocumentChunk(
        documentId: asStringD(firstNonNull(j, ['document_id', 'id'])),
        chunkId: asStringD(firstNonNull(j, ['chunk_id', 'id'])),
        filename: asStringD(firstNonNull(j, ['filename', 'title'])),
        section: asString(j['section']),
        article: asString(firstNonNull(j, ['article', 'clause'])),
        semester: asString(j['semester']),
        text: asStringD(firstNonNull(j, ['text', 'content', 'body'])),
        highlight: asString(firstNonNull(j, ['highlight', 'quote'])),
      );
}

class TodoItem {
  const TodoItem({
    required this.id,
    required this.type,
    required this.title,
    this.subtitle,
    this.dueAt,
    this.status,
    this.group,
    this.actionLabel = '去办理',
    this.actionType,
    this.refType,
    this.refId,
    this.highPriority = false,
  });

  final String id;
  final String type;
  final String title;
  final String? subtitle;
  final DateTime? dueAt;
  final String? status;
  final String? group;
  final String actionLabel;
  final String? actionType;
  final String? refType;
  final String? refId;
  final bool highPriority;

  bool get isEnrollment => group == 'enrollment' || type == 'registration';

  factory TodoItem.fromJson(Map<String, dynamic> j) {
    final action = asMap(j['action']);
    return TodoItem(
      id: asStringD(j['id']),
      type: asStringD(j['type'], 'task'),
      title: asStringD(firstNonNull(j, ['title', 'name'])),
      subtitle: asString(firstNonNull(j, ['subtitle', 'summary', 'desc'])),
      dueAt: asDate(firstNonNull(j, ['due_at', 'dueAt', 'deadline', 'expires_at'])),
      status: asString(j['status']),
      group: asString(j['group']),
      actionLabel: asStringD(
        firstNonNull(action, ['label']) ?? j['action_label'] ?? j['button'],
        '去办理',
      ),
      actionType: asString(firstNonNull(action, ['type']) ?? j['action_type']),
      refType: asString(firstNonNull(j, ['ref_type', 'refType']) ?? action['ref_type']),
      refId: asString(firstNonNull(j, ['ref_id', 'refId']) ??
          firstNonNull(asMap(action['ref']), ['id']) ??
          action['ref_id']),
      highPriority: asBool(firstNonNull(j, ['high_priority', 'priority'])),
    );
  }
}

class ReminderItem {
  const ReminderItem({
    required this.id,
    required this.category,
    required this.title,
    this.body,
    this.citations = const [],
    this.action,
    this.at,
  });

  final String id;
  final String category;
  final String title;
  final String? body;
  final List<Citation> citations;
  final AnswerAction? action;
  final DateTime? at;

  factory ReminderItem.fromJson(Map<String, dynamic> j) => ReminderItem(
        id: asStringD(j['id']),
        category: asStringD(j['category'], 'deadline'),
        title: asStringD(j['title']),
        body: asString(firstNonNull(j, ['body', 'reason', 'message', 'content'])),
        citations: asObjList(j['citations'], Citation.fromJson),
        action: asObj(j['action'], AnswerAction.fromJson),
        at: asDate(firstNonNull(j, ['at', 'due_at', 'created_at'])),
      );
}

class ReminderBundle {
  const ReminderBundle({
    this.items = const [],
    this.mutedCategories = const {},
  });

  final List<ReminderItem> items;
  final Set<String> mutedCategories;

  factory ReminderBundle.fromJson(dynamic raw) {
    if (raw is List) {
      return ReminderBundle(items: asObjList(raw, ReminderItem.fromJson));
    }
    final j = asMap(raw);
    final muted = asList(firstNonNull(j, ['muted_categories', 'mutes', 'muted']))
        .map((e) {
          if (e is String) return e;
          if (e is Map) return asStringD(e['category'] ?? e['cat']);
          return '';
        })
        .where((e) => e.isNotEmpty)
        .toSet();
    return ReminderBundle(
      items: asObjList(firstNonNull(j, ['items', 'reminders']) ?? j['data'], ReminderItem.fromJson),
      mutedCategories: muted,
    );
  }
}

class FieldSource {
  const FieldSource({
    required this.field,
    required this.label,
    required this.value,
    required this.source,
  });

  final String field;
  final String label;
  final String value;
  /// profile | manual | extracted | unauthorized
  final String source;

  String get sourceLabel {
    switch (source) {
      case 'profile':
        return '来自档案预填';
      case 'extracted':
        return '从材料识别，请核对';
      case 'unauthorized':
        return '未授权，未使用';
      case 'manual':
      default:
        return '本次手填';
    }
  }

  factory FieldSource.fromJson(Map<String, dynamic> j) => FieldSource(
        field: asStringD(firstNonNull(j, ['field', 'key', 'name'])),
        label: asStringD(firstNonNull(j, ['label', 'title']), asStringD(j['field'])),
        value: asStringD(firstNonNull(j, ['value', 'text'])),
        source: asStringD(j['source'], 'manual'),
      );
}

class AttachmentInfo {
  const AttachmentInfo({
    required this.id,
    required this.filename,
    this.url,
    this.localPath,
    this.expiresAt,
    this.kind,
  });

  final String id;
  final String filename;
  final String? url;
  final String? localPath;
  final DateTime? expiresAt;
  final String? kind;

  bool get expired => expiresAt != null && DateTime.now().isAfter(expiresAt!);

  String get validityLabel {
    if (expiresAt == null) return '有效期未标注';
    if (expired) return '已过期';
    final days = expiresAt!.difference(DateTime.now()).inDays;
    if (days <= 0) return '今日到期';
    return '有效期至 ${_fmt(expiresAt!)}（剩 $days 天）';
  }

  static String _fmt(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  factory AttachmentInfo.fromJson(Map<String, dynamic> j) => AttachmentInfo(
        id: asStringD(firstNonNull(j, ['id', 'attachment_id'])),
        filename: asStringD(firstNonNull(j, ['filename', 'name', 'title']), '附件'),
        url: asString(firstNonNull(j, ['url', 'thumbnail_url'])),
        localPath: asString(firstNonNull(j, ['local_path', 'path'])),
        expiresAt: asDate(firstNonNull(j, ['expires_at', 'expire_at', 'valid_until'])),
        kind: asString(firstNonNull(j, ['kind', 'type', 'category'])),
      );
}

class ApproverInfo {
  const ApproverInfo({
    this.id,
    required this.name,
    required this.role,
    this.order = 1,
    this.status,
    this.comment,
  });

  final String? id;
  final String name;
  final String role;
  final int order;
  final String? status;
  final String? comment;

  factory ApproverInfo.fromJson(Map<String, dynamic> j) => ApproverInfo(
        id: asString(j['id']),
        name: asStringD(j['name']),
        role: asStringD(firstNonNull(j, ['role', 'role_label']), '审批人'),
        order: asInt(j['order']) ?? 1,
        status: asString(j['status']),
        comment: asString(firstNonNull(j, ['comment', 'reason'])),
      );
}

class MissingItem {
  const MissingItem({required this.field, required this.message});

  final String field;
  final String message;

  factory MissingItem.fromJson(Map<String, dynamic> j) => MissingItem(
        field: asStringD(firstNonNull(j, ['field', 'name'])),
        message: asStringD(firstNonNull(j, ['message', 'reason', 'label'])),
      );
}

class ValidationResult {
  const ValidationResult({
    required this.ok,
    this.missing = const [],
    this.message,
  });

  final bool ok;
  final List<MissingItem> missing;
  final String? message;

  factory ValidationResult.fromJson(dynamic raw) {
    final j = asMap(raw);
    final missingRaw = firstNonNull(j, ['missing', 'details']) ??
        (j['details'] is Map ? asMap(j['details'])['missing'] : null);
    return ValidationResult(
      ok: asBool(firstNonNull(j, ['ok', 'passed', 'valid']), j.isEmpty),
      missing: asObjList(missingRaw, MissingItem.fromJson),
      message: asString(firstNonNull(j, ['message', 'reason'])),
    );
  }
}

class LeaveRecord {
  const LeaveRecord({
    required this.id,
    required this.status,
    this.reason,
    this.destination,
    this.startAt,
    this.endAt,
    this.durationText,
    this.fields = const [],
    this.attachments = const [],
    this.approvers = const [],
    this.citations = const [],
    this.validation = const ValidationResult(ok: true),
    this.conflictNote,
    this.legalNote,
    this.reusable = const [],
  });

  final String id;
  final String status;
  final String? reason;
  final String? destination;
  final DateTime? startAt;
  final DateTime? endAt;
  final String? durationText;
  final List<FieldSource> fields;
  final List<AttachmentInfo> attachments;
  final List<ApproverInfo> approvers;
  final List<Citation> citations;
  final ValidationResult validation;
  final String? conflictNote;
  final String? legalNote;
  final List<AttachmentInfo> reusable;

  bool get canConfirm =>
      validation.ok &&
      (status == 'draft' || status == 'pending_confirm' || status == 'rejected');

  factory LeaveRecord.fromJson(Map<String, dynamic> j) {
    final validationRaw = firstNonNull(j, ['validation', 'check', 'validate']);
    return LeaveRecord(
      id: asStringD(j['id']),
      status: asStringD(j['status'], 'draft'),
      reason: asString(j['reason']),
      destination: asString(firstNonNull(j, ['destination', 'where', 'goto'])),
      startAt: asDate(firstNonNull(j, ['start_at', 'startAt', 'begin_at'])),
      endAt: asDate(firstNonNull(j, ['end_at', 'endAt', 'finish_at'])),
      durationText: asString(firstNonNull(j, ['duration_text', 'duration', 'length'])),
      fields: asObjList(firstNonNull(j, ['fields', 'prefills', 'prefill']), FieldSource.fromJson),
      attachments: asObjList(j['attachments'], AttachmentInfo.fromJson),
      approvers: asObjList(firstNonNull(j, ['approvers', 'approval_chain']), ApproverInfo.fromJson),
      citations: asObjList(j['citations'], Citation.fromJson),
      validation: validationRaw == null
          ? const ValidationResult(ok: true)
          : ValidationResult.fromJson(validationRaw),
      conflictNote: asString(firstNonNull(j, ['conflict_note', 'exam_conflict'])),
      legalNote: asString(firstNonNull(j, ['legal_note', 'effect_note'])),
      reusable: asObjList(firstNonNull(j, ['reusable', 'reuse_attachments']), AttachmentInfo.fromJson),
    );
  }
}

class AidMatch {
  const AidMatch({
    required this.programId,
    required this.title,
    this.reason,
    this.citations = const [],
    this.dueAt,
    this.requiredAuthFields = const [],
    this.needsAuthorization = false,
  });

  final String programId;
  final String title;
  final String? reason;
  final List<Citation> citations;
  final DateTime? dueAt;
  final List<String> requiredAuthFields;
  final bool needsAuthorization;

  factory AidMatch.fromJson(Map<String, dynamic> j) => AidMatch(
        programId: asStringD(firstNonNull(j, ['program_id', 'id'])),
        title: asStringD(firstNonNull(j, ['title', 'name'])),
        reason: asString(firstNonNull(j, ['reason', 'match_reason', 'why'])),
        citations: asObjList(j['citations'], Citation.fromJson),
        dueAt: asDate(firstNonNull(j, ['due_at', 'deadline'])),
        requiredAuthFields: asList(firstNonNull(j, ['required_auth_fields', 'required_fields']))
            .map((e) => e.toString())
            .toList(),
        needsAuthorization: asBool(j['needs_authorization']),
      );
}

class AidDraft {
  const AidDraft({
    required this.id,
    required this.programId,
    required this.title,
    required this.status,
    this.fields = const [],
    this.attachments = const [],
    this.citations = const [],
    this.validation = const ValidationResult(ok: true),
    this.packageDownloadUrl,
    this.statement,
  });

  final String id;
  final String programId;
  final String title;
  final String status;
  final List<FieldSource> fields;
  final List<AttachmentInfo> attachments;
  final List<Citation> citations;
  final ValidationResult validation;
  final String? packageDownloadUrl;
  final String? statement;

  factory AidDraft.fromJson(Map<String, dynamic> j) => AidDraft(
        id: asStringD(j['id']),
        programId: asStringD(firstNonNull(j, ['program_id', 'programId'])),
        title: asStringD(firstNonNull(j, ['title', 'program_title']), '奖助申请草稿'),
        status: asStringD(j['status'], 'draft'),
        fields: asObjList(firstNonNull(j, ['fields', 'prefills']), FieldSource.fromJson),
        attachments: asObjList(j['attachments'], AttachmentInfo.fromJson),
        citations: asObjList(j['citations'], Citation.fromJson),
        validation: j['validation'] == null
            ? const ValidationResult(ok: true)
            : ValidationResult.fromJson(j['validation']),
        packageDownloadUrl: asString(firstNonNull(j, ['package_url', 'download_url'])),
        statement: asString(firstNonNull(j, ['statement', 'personal_statement'])),
      );
}

class TaskItem {
  const TaskItem({
    required this.id,
    required this.type,
    required this.title,
    this.body,
    this.dueAt,
    this.audience,
    this.submitMode,
    this.citations = const [],
    this.status,
    this.capacity,
    this.signedUp,
    this.requirements = const [],
    this.signupValidation,
    this.prefills = const [],
    this.location,
    this.timeText,
    this.needReview = false,
  });

  final String id;
  final String type;
  final String title;
  final String? body;
  final DateTime? dueAt;
  final String? audience;
  final String? submitMode;
  final List<Citation> citations;
  final String? status;
  final int? capacity;
  final int? signedUp;
  final List<String> requirements;
  final ValidationResult? signupValidation;
  final List<FieldSource> prefills;
  final String? location;
  final String? timeText;
  final bool needReview;

  factory TaskItem.fromJson(Map<String, dynamic> j) => TaskItem(
        id: asStringD(j['id']),
        type: asStringD(j['type'], 'homework'),
        title: asStringD(j['title']),
        body: asString(firstNonNull(j, ['body', 'description', 'content'])),
        dueAt: asDate(firstNonNull(j, ['due_at', 'deadline'])),
        audience: asString(firstNonNull(j, ['audience', 'target', 'scope'])),
        submitMode: asString(firstNonNull(j, ['submit_mode', 'mode', 'submit_type'])),
        citations: asObjList(j['citations'], Citation.fromJson),
        status: asString(j['status']),
        capacity: asInt(firstNonNull(j, ['capacity', 'quota'])),
        signedUp: asInt(firstNonNull(j, ['signed_up', 'enrolled', 'count'])),
        requirements: asList(j['requirements']).map((e) => e.toString()).toList(),
        signupValidation: j['validation'] == null && j['signup_validation'] == null
            ? null
            : ValidationResult.fromJson(j['validation'] ?? j['signup_validation']),
        prefills: asObjList(firstNonNull(j, ['prefills', 'fields']), FieldSource.fromJson),
        location: asString(firstNonNull(j, ['location', 'place'])),
        timeText: asString(firstNonNull(j, ['time_text', 'activity_time'])),
        needReview: asBool(firstNonNull(j, ['need_review', 'require_review'])),
      );
}

class ProgressRow {
  const ProgressRow({
    required this.userId,
    required this.name,
    this.className,
    required this.status,
    this.at,
    this.overdue = false,
  });

  final String userId;
  final String name;
  final String? className;
  final String status;
  final DateTime? at;
  final bool overdue;

  factory ProgressRow.fromJson(Map<String, dynamic> j) => ProgressRow(
        userId: asStringD(firstNonNull(j, ['user_id', 'id', 'student_id'])),
        name: asStringD(j['name']),
        className: asString(firstNonNull(j, ['class_name', 'klass', 'class'])),
        status: asStringD(j['status'], 'pending'),
        at: asDate(firstNonNull(j, ['at', 'submitted_at', 'completed_at'])),
        overdue: asBool(firstNonNull(j, ['overdue', 'flagged', 'red'])),
      );
}

class TaskProgress {
  const TaskProgress({
    required this.taskId,
    this.title,
    this.total = 0,
    this.completed = 0,
    this.rows = const [],
  });

  final String taskId;
  final String? title;
  final int total;
  final int completed;
  final List<ProgressRow> rows;

  factory TaskProgress.fromJson(Map<String, dynamic> j) => TaskProgress(
        taskId: asStringD(firstNonNull(j, ['task_id', 'id'])),
        title: asString(j['title']),
        total: asInt(j['total']) ?? asList(firstNonNull(j, ['rows', 'items', 'students'])).length,
        completed: asInt(firstNonNull(j, ['completed', 'done'])) ?? 0,
        rows: asObjList(firstNonNull(j, ['rows', 'items', 'students']), ProgressRow.fromJson),
      );
}

class ApprovalItem {
  const ApprovalItem({
    required this.id,
    required this.type,
    required this.title,
    required this.applicantName,
    this.summary,
    this.submittedAt,
    this.status = 'pending',
    this.leave,
    this.citations = const [],
    this.attachments = const [],
    this.validation,
    this.fields = const [],
  });

  final String id;
  final String type;
  final String title;
  final String applicantName;
  final String? summary;
  final DateTime? submittedAt;
  final String status;
  final LeaveRecord? leave;
  final List<Citation> citations;
  final List<AttachmentInfo> attachments;
  final ValidationResult? validation;
  final List<FieldSource> fields;

  factory ApprovalItem.fromJson(Map<String, dynamic> j) {
    final leave = asObj(j['leave'] ?? (j['type'] == 'leave' ? j : null), LeaveRecord.fromJson);
    return ApprovalItem(
      id: asStringD(j['id']),
      type: asStringD(j['type'], 'leave'),
      title: asStringD(firstNonNull(j, ['title', 'subject']), '请假审批'),
      applicantName: asStringD(firstNonNull(j, ['applicant_name', 'student_name', 'applicant'])),
      summary: asString(firstNonNull(j, ['summary', 'reason'])),
      submittedAt: asDate(firstNonNull(j, ['submitted_at', 'created_at'])),
      status: asStringD(j['status'], 'pending'),
      leave: leave,
      citations: asObjList(j['citations'], Citation.fromJson),
      attachments: asObjList(j['attachments'], AttachmentInfo.fromJson),
      validation: j['validation'] == null ? null : ValidationResult.fromJson(j['validation']),
      fields: asObjList(j['fields'], FieldSource.fromJson),
    );
  }
}

class ApplicationItem {
  const ApplicationItem({
    required this.id,
    required this.kind,
    required this.title,
    required this.status,
    this.updatedAt,
    this.refId,
  });

  final String id;
  final String kind;
  final String title;
  final String status;
  final DateTime? updatedAt;
  final String? refId;

  factory ApplicationItem.fromJson(Map<String, dynamic> j) => ApplicationItem(
        id: asStringD(j['id']),
        kind: asStringD(firstNonNull(j, ['kind', 'type'])),
        title: asStringD(j['title']),
        status: asStringD(j['status']),
        updatedAt: asDate(firstNonNull(j, ['updated_at', 'created_at'])),
        refId: asString(firstNonNull(j, ['ref_id', 'target_id'])),
      );
}

class ConfirmPayload {
  const ConfirmPayload({
    required this.title,
    this.headline,
    this.prefills = const [],
    this.manuals = const [],
    this.attachments = const [],
    this.approvers = const [],
    this.citations = const [],
    this.warnings = const [],
    this.legalNote,
    required this.submitLabel,
  });

  final String title;
  final String? headline;
  final List<FieldSource> prefills;
  final List<FieldSource> manuals;
  final List<AttachmentInfo> attachments;
  final List<ApproverInfo> approvers;
  final List<Citation> citations;
  final List<String> warnings;
  final String? legalNote;
  final String submitLabel;

  static ConfirmPayload fromLeave(LeaveRecord leave, {String submitLabel = '确认提交'}) {
    final prefills = leave.fields.where((f) => f.source == 'profile' || f.source == 'unauthorized').toList();
    final manuals = leave.fields.where((f) => f.source != 'profile' && f.source != 'unauthorized').toList();
    return ConfirmPayload(
      title: '确认请假信息',
      headline: leave.durationText,
      prefills: prefills,
      manuals: manuals,
      attachments: leave.attachments,
      approvers: leave.approvers,
      citations: leave.citations,
      warnings: [
        if (leave.conflictNote != null && leave.conflictNote!.isNotEmpty) leave.conflictNote!,
      ],
      legalNote: leave.legalNote ??
          '提交后，审批前可以撤回；进入审批后需联系审批人退回。系统不会代替你确认，也不会代替老师审批。',
      submitLabel: submitLabel,
    );
  }

  static ConfirmPayload fromAid(AidDraft draft) {
    return ConfirmPayload(
      title: '确认奖助申请草稿',
      headline: draft.title,
      prefills: draft.fields.where((f) => f.source == 'profile' || f.source == 'unauthorized').toList(),
      manuals: draft.fields.where((f) => f.source != 'profile' && f.source != 'unauthorized').toList(),
      attachments: draft.attachments,
      citations: draft.citations,
      legalNote: '确认后不会自动向学校提交。若暂无校级对接，状态为「草稿已确认，待按指引报送」，并可下载材料包。系统不会代替你提交。',
      submitLabel: '确认草稿',
    );
  }

  static ConfirmPayload fromTask(TaskItem task, {required String submitLabel}) {
    return ConfirmPayload(
      title: task.type == 'volunteer' ? '确认报名信息' : '确认提交',
      headline: task.title,
      prefills: task.prefills.where((f) => f.source == 'profile' || f.source == 'unauthorized').toList(),
      manuals: task.prefills.where((f) => f.source != 'profile' && f.source != 'unauthorized').toList(),
      citations: task.citations,
      legalNote: '请核对以上信息后再确认。系统不会代替你提交。',
      submitLabel: submitLabel,
    );
  }
}
