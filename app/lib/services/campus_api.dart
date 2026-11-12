import '../models/models.dart';

abstract class CampusApi {
  Future<bool> pingHealth();

  Future<LoginResult> login(String username, String password);

  Future<User> me();

  Future<Profile> getProfile();

  Future<Profile> patchProfile(Map<String, dynamic> patch);

  Future<void> authorize({
    required String purpose,
    required List<String> fields,
    required String refType,
    String? refId,
  });

  Future<AskResult> ask({
    required String text,
    List<String> attachmentIds = const [],
    Map<String, String>? slots,
  });

  Future<AttachmentInfo> uploadAttachment(String path, {String? filename, String? kind});

  Future<DocumentChunk> getChunk(String documentId, String chunkId);

  Future<List<TodoItem>> todos({String? status});

  Future<ReminderBundle> reminders();

  Future<void> muteReminderCategory(String cat, {bool muted = true});

  Future<LeaveRecord> createLeave({
    String? text,
    List<String> attachmentIds = const [],
    Map<String, dynamic>? fields,
  });

  Future<LeaveRecord> extractLeave(String id);

  Future<LeaveRecord> getLeave(String id);

  Future<LeaveRecord> confirmLeave(String id, {Map<String, dynamic>? fields});

  Future<void> withdrawLeave(String id);

  Future<LeaveRecord> returnLeave(String id, {DateTime? returnedAt});

  Future<List<ApprovalItem>> approvals({String? type});

  Future<void> decideApproval(String id, {required String decision, String? comment});

  Future<List<AidMatch>> aidMatches();

  Future<AidDraft> createAidDraft(String programId);

  Future<AidDraft> getAidDraft(String id);

  Future<AidDraft> confirmAidDraft(String id, {Map<String, dynamic>? fields});

  Future<TaskItem> getTask(String id);

  Future<TaskItem> submitTask(
    String id, {
    String? note,
    List<String> attachmentIds = const [],
    Map<String, dynamic>? fields,
  });

  Future<TaskItem> createTask({
    required String type,
    required String title,
    String? body,
    DateTime? dueAt,
    String? audience,
    Map<String, dynamic>? extra,
  });

  Future<TaskProgress> taskProgress(String id);

  Future<List<ApplicationItem>> myApplications();

  Future<List<AttachmentInfo>> myAttachments();
}
