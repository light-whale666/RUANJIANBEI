import '../models/models.dart';
import '../services/api_exception.dart';
import '../services/campus_api.dart';
import 'fixtures.dart';

/// 本地预览数据源。不连接服务器，也不使用任何真实密码。
class DemoCampusApi implements CampusApi {
  DemoCampusApi({required this.roleKey}) {
    _bootstrap();
  }

  final String roleKey; // freshman | senior | teacher | counselor

  late User _user;
  late Profile _profile;
  final Map<String, LeaveRecord> _leaves = {};
  final Map<String, TaskItem> _tasks = {};
  final Map<String, AidDraft> _drafts = {};
  final List<TodoItem> _todos = [];
  final List<ReminderItem> _reminders = [];
  final Set<String> _muted = {};
  final List<ApprovalItem> _approvals = [];
  final List<ApplicationItem> _applications = [];
  final List<AttachmentInfo> _attachments = [];
  final Map<String, TaskProgress> _progress = {};
  int _seq = 100;

  String _id(String prefix) => '$prefix${_seq++}';

  void _bootstrap() {
    switch (roleKey) {
      case 'senior':
        _user = seniorUser();
        _profile = seniorProfile();
        _seedSenior();
        break;
      case 'teacher':
        _user = teacherUser();
        _profile = teacherProfile();
        _seedTeacher();
        break;
      case 'counselor':
        _user = counselorUser();
        _profile = counselorProfile();
        _seedCounselor();
        break;
      default:
        _user = freshmanUser();
        _profile = freshmanProfile();
        _seedFreshman();
    }
  }

  void _seedFreshman() {
    _todos.addAll([
      TodoItem(
        id: 'td_profile',
        type: 'registration',
        title: '完善个人档案基础信息',
        subtitle: '入学报到需要核对一次',
        dueAt: DateTime(2026, 11, 15),
        group: 'enrollment',
        actionLabel: '去核对',
        actionType: 'profile',
        refType: 'profile',
      ),
      TodoItem(
        id: 'td_dorm',
        type: 'registration',
        title: '确认宿舍床位',
        subtitle: '6号楼402室 3号床',
        dueAt: DateTime(2026, 11, 15),
        group: 'enrollment',
        actionLabel: '去确认',
        actionType: 'task',
        refType: 'task',
        refId: 'task_dorm',
      ),
      TodoItem(
        id: 'td_enroll_read',
        type: 'registration',
        title: '阅读《2026级新生入学须知》并确认',
        subtitle: '11月15日前完成',
        dueAt: DateTime(2026, 11, 15),
        group: 'enrollment',
        actionLabel: '去完成',
        actionType: 'task',
        refType: 'task',
        refId: 'task_enroll_read',
        highPriority: true,
      ),
      TodoItem(
        id: 'td_photo',
        type: 'registration',
        title: '上传证件照',
        subtitle: '用于学生证制作',
        dueAt: DateTime(2026, 11, 15),
        group: 'enrollment',
        actionLabel: '去上传',
        actionType: 'task',
        refType: 'task',
        refId: 'task_photo',
      ),
      TodoItem(
        id: 'td_hw1',
        type: 'homework',
        title: '高等数学第一次作业',
        subtitle: '李承泽老师 · 上传解答即可',
        dueAt: DateTime(2026, 11, 12, 23, 59),
        actionLabel: '去提交',
        actionType: 'task',
        refType: 'task',
        refId: 'task_hw_math',
      ),
      TodoItem(
        id: 'td_vol',
        type: 'volunteer',
        title: '迎新志愿服务招募',
        subtitle: '11月16日 图书馆 · 余 8 个名额',
        dueAt: DateTime(2026, 11, 14, 18),
        actionLabel: '去报名',
        actionType: 'task',
        refType: 'task',
        refId: 'task_vol_welcome',
      ),
    ]);
    _reminders.add(
      const ReminderItem(
        id: 'rm_enroll',
        category: 'deadline',
        title: '入学须知确认将于 11 月 15 日截止',
        body: '未完成关键报到项将由辅导员跟进。',
        citations: [citeEnroll],
        action: AnswerAction(type: 'task', label: '去完成', ref: {'id': 'task_enroll_read'}),
      ),
    );
    _tasks['task_dorm'] = TaskItem(
      id: 'task_dorm',
      type: 'registration',
      title: '确认宿舍床位',
      body: '请核对自己的宿舍与床位。如有误，请在确认页备注后提交，由辅导员核实。',
      dueAt: DateTime(2026, 11, 15),
      submitMode: 'confirm',
      citations: [citeEnroll],
      prefills: [
        FieldSource(field: 'dorm', label: '宿舍', value: '6号楼402', source: 'profile'),
        FieldSource(field: 'bed', label: '床位', value: '3号床', source: 'profile'),
      ],
    );
    _tasks['task_enroll_read'] = TaskItem(
      id: 'task_enroll_read',
      type: 'registration',
      title: '阅读《2026级新生入学须知》并确认',
      body: '请阅读入学须知相关条款后确认已了解报到安排。',
      dueAt: DateTime(2026, 11, 15),
      submitMode: 'confirm',
      citations: [citeEnroll],
    );
    _tasks['task_photo'] = TaskItem(
      id: 'task_photo',
      type: 'registration',
      title: '上传证件照',
      body: '请上传近期免冠证件照，用于学生证制作。',
      dueAt: DateTime(2026, 11, 15),
      submitMode: 'file',
    );
    _tasks['task_hw_math'] = TaskItem(
      id: 'task_hw_math',
      type: 'homework',
      title: '高等数学第一次作业',
      body: '完成教材第一章习题 1–12，上传清晰照片或 PDF。初版不做自动批改。',
      dueAt: DateTime(2026, 11, 12, 23, 59),
      audience: '高等数学（26软件1班）',
      submitMode: 'file',
    );
    _tasks['task_vol_welcome'] = TaskItem(
      id: 'task_vol_welcome',
      type: 'volunteer',
      title: '迎新志愿服务招募',
      body: '在图书馆协助新生领取材料、引导路线。需当天在校，不限年级。',
      dueAt: DateTime(2026, 11, 14, 18),
      submitMode: 'signup',
      location: '图书馆一层大厅',
      timeText: '2026年11月16日 9:00–16:00',
      capacity: 20,
      signedUp: 12,
      prefills: [
        FieldSource(field: 'name', label: '姓名', value: '陈晓桐', source: 'profile'),
        FieldSource(field: 'class', label: '班级', value: '26软件1班', source: 'profile'),
        FieldSource(field: 'phone', label: '手机', value: '13800002101', source: 'profile'),
        FieldSource(field: 'slot', label: '可参加时段', value: '', source: 'manual'),
      ],
    );
  }

  void _seedSenior() {
    _todos.addAll([
      TodoItem(
        id: 'td_return',
        type: 'leave_return',
        title: '请假待销假',
        subtitle: '11月10日–11日 事假，明日到期',
        dueAt: DateTime(2026, 11, 11, 23, 59),
        actionLabel: '去销假',
        actionType: 'leave_return',
        refType: 'leave',
        refId: 'leave_open',
        highPriority: true,
      ),
      TodoItem(
        id: 'td_aid',
        type: 'aid',
        title: '国家励志奖学金：可能符合',
        subtitle: '成绩前 30% 且已完成困难认定授权',
        dueAt: DateTime(2026, 12, 5),
        actionLabel: '去查看草稿',
        actionType: 'aid',
        refType: 'aid',
        refId: 'aid_lizhi',
      ),
      TodoItem(
        id: 'td_hw_compile',
        type: 'homework',
        title: '编译原理第二次作业',
        subtitle: '李承泽老师',
        dueAt: DateTime(2026, 11, 13, 23, 59),
        actionLabel: '去提交',
        actionType: 'task',
        refType: 'task',
        refId: 'task_hw_compile',
      ),
      TodoItem(
        id: 'td_vol2',
        type: 'volunteer',
        title: '社区科普志愿服务',
        subtitle: '仅限已完成安全培训的同学',
        dueAt: DateTime(2026, 11, 18),
        actionLabel: '去报名',
        actionType: 'task',
        refType: 'task',
        refId: 'task_vol_train',
      ),
    ]);
    _reminders.addAll([
      const ReminderItem(
        id: 'rm_return',
        category: 'deadline',
        title: '请假将于 11 月 11 日到期，请按时销假',
        body: '假期期满须在返校当日办理销假。',
        citations: [citeLeave2026Return],
        action: AnswerAction(type: 'leave_return', label: '去销假', ref: {'id': 'leave_open'}),
      ),
      const ReminderItem(
        id: 'rm_aid',
        category: 'eligibility',
        title: '国家励志奖学金：可能符合申请条件',
        body: '匹配理由：上一学年成绩位于本专业前 30%，且已授权困难认定结果为通过。不会自动提交。',
        citations: [citeAid],
        action: AnswerAction(type: 'aid', label: '查看并生成草稿', ref: {'id': 'aid_lizhi'}),
      ),
    ]);
    _leaves['leave_open'] = LeaveRecord(
      id: 'leave_open',
      status: 'pending_return',
      reason: '回家办理户口事项',
      destination: '杭州',
      startAt: DateTime(2026, 11, 10, 8),
      endAt: DateTime(2026, 11, 11, 18),
      durationText: '1 天（跨天）',
      fields: const [
        FieldSource(field: 'name', label: '姓名', value: '刘振宇', source: 'profile'),
        FieldSource(field: 'student_no', label: '学号', value: '2023210108', source: 'profile'),
        FieldSource(field: 'class', label: '班级', value: '23软件2班', source: 'profile'),
        FieldSource(field: 'reason', label: '原因', value: '回家办理户口事项', source: 'manual'),
        FieldSource(field: 'time', label: '起止时间', value: '2026-11-10 08:00 至 2026-11-11 18:00', source: 'manual'),
      ],
      approvers: const [
        ApproverInfo(name: '王雨晨', role: '辅导员', order: 1, status: 'approved'),
      ],
      citations: const [citeLeave2026, citeLeave2026Return],
      legalNote: '批准后已写入待办。返校后请确认销假。本演示环境由辅导员终审并备案。',
    );
    _applications.add(const ApplicationItem(
      id: 'leave_open',
      kind: 'leave',
      title: '事假 11月10日–11日',
      status: 'pending_return',
      refId: 'leave_open',
    ));
    _attachments.add(AttachmentInfo(
      id: 'att_hukou',
      filename: '户口办理通知.jpg',
      kind: 'note',
      expiresAt: DateTime(2026, 11, 17),
    ));
    _tasks['task_hw_compile'] = TaskItem(
      id: 'task_hw_compile',
      type: 'homework',
      title: '编译原理第二次作业',
      body: '完成语法分析实验报告并上传。',
      dueAt: DateTime(2026, 11, 13, 23, 59),
      audience: '编译原理（23软件2班）',
      submitMode: 'file',
    );
    _tasks['task_vol_train'] = TaskItem(
      id: 'task_vol_train',
      type: 'volunteer',
      title: '社区科普志愿服务',
      body: '需已完成学院安全培训。未完成培训的同学将被当场拦住并说明依据。',
      dueAt: DateTime(2026, 11, 18),
      submitMode: 'signup',
      location: '社区活动中心',
      timeText: '2026年11月22日 14:00–17:00',
      requirements: ['已完成学院安全培训'],
      signupValidation: ValidationResult(
        ok: false,
        missing: [MissingItem(field: 'training', message: '未查询到你的学院安全培训完成记录，不符合本次招募条件。')],
        message: '不符合报名条件',
      ),
      prefills: [
        FieldSource(field: 'name', label: '姓名', value: '刘振宇', source: 'profile'),
        FieldSource(field: 'phone', label: '手机', value: '13700002108', source: 'profile'),
      ],
    );
  }

  void _seedTeacher() {
    _todos.add(
      const TodoItem(
        id: 'td_review_hw',
        type: 'homework',
        title: '查看「高等数学第一次作业」提交进度',
        subtitle: '26软件1班 · 已交 18 / 32',
        actionLabel: '看名单',
        actionType: 'progress',
        refType: 'task',
        refId: 'task_hw_math',
      ),
    );
    _tasks['task_hw_math'] = TaskItem(
      id: 'task_hw_math',
      type: 'homework',
      title: '高等数学第一次作业',
      body: '完成教材第一章习题 1–12。',
      dueAt: DateTime(2026, 11, 12, 23, 59),
      audience: '高等数学（26软件1班）',
      submitMode: 'file',
    );
    _progress['task_hw_math'] = TaskProgress(
      taskId: 'task_hw_math',
      title: '高等数学第一次作业',
      total: 32,
      completed: 18,
      rows: [
        ProgressRow(userId: 'stu_chen', name: '陈晓桐', className: '26软件1班', status: 'pending', overdue: true),
        ProgressRow(userId: 's2', name: '周启明', className: '26软件1班', status: 'submitted', at: DateTime(2026, 11, 10, 9, 12)),
        ProgressRow(userId: 's3', name: '苏晚', className: '26软件1班', status: 'submitted', at: DateTime(2026, 11, 9, 21, 4)),
        ProgressRow(userId: 's4', name: '林小北', className: '26软件1班', status: 'pending'),
      ],
    );
  }

  void _seedCounselor() {
    _todos.add(
      const TodoItem(
        id: 'td_appr',
        type: 'leave_confirm',
        title: '待审批：陈晓桐的短假申请',
        subtitle: '11月11日上午 就医',
        actionLabel: '去审批',
        actionType: 'approval',
        refType: 'approval',
        refId: 'appr_chen',
        highPriority: true,
      ),
    );
    final leave = LeaveRecord(
      id: 'leave_chen',
      status: 'approving',
      reason: '上午去医院复查',
      destination: '校医院',
      startAt: DateTime(2026, 11, 11, 8),
      endAt: DateTime(2026, 11, 11, 12),
      durationText: '4 小时（短假，不跨天）',
      fields: const [
        FieldSource(field: 'name', label: '姓名', value: '陈晓桐', source: 'profile'),
        FieldSource(field: 'student_no', label: '学号', value: '2026210101', source: 'profile'),
        FieldSource(field: 'class', label: '班级', value: '26软件1班', source: 'profile'),
        FieldSource(field: 'phone', label: '联系方式', value: '13800002101', source: 'profile'),
        FieldSource(field: 'reason', label: '原因', value: '上午去医院复查', source: 'manual'),
        FieldSource(field: 'time', label: '起止时间', value: '2026-11-11 08:00 至 12:00', source: 'manual'),
      ],
      attachments: const [
        AttachmentInfo(id: 'att_case', filename: '校医院挂号单.jpg', kind: 'receipt'),
      ],
      approvers: const [
        ApproverInfo(name: '王雨晨', role: '辅导员', order: 1, status: 'pending'),
      ],
      citations: const [citeLeave2026],
      conflictNote: '未发现已登记考试冲突，请自行确认。本演示环境无年级负责人，由辅导员终审并备案。',
    );
    _leaves['leave_chen'] = leave;
    _approvals.add(ApprovalItem(
      id: 'appr_chen',
      type: 'leave',
      title: '短假审批',
      applicantName: '陈晓桐',
      summary: '11月11日 08:00–12:00 就医复查',
      submittedAt: DateTime(2026, 11, 10, 20, 15),
      status: 'pending',
      leave: leave,
      citations: const [citeLeave2026],
      attachments: leave.attachments,
      validation: const ValidationResult(ok: true, message: '材料齐全，属短假，辅导员审批即可。'),
      fields: leave.fields,
    ));
    _progress['enroll_26'] = TaskProgress(
      taskId: 'enroll_26',
      title: '26软件1班入学报到',
      total: 4,
      completed: 1,
      rows: [
        ProgressRow(userId: 'stu_chen', name: '陈晓桐', className: '26软件1班', status: 'pending', overdue: true),
        ProgressRow(userId: 's2', name: '周启明', className: '26软件1班', status: 'submitted'),
        ProgressRow(userId: 's3', name: '苏晚', className: '26软件1班', status: 'pending'),
        ProgressRow(userId: 's4', name: '林小北', className: '26软件1班', status: 'pending', overdue: true),
      ],
    );
    _tasks['enroll_26'] = TaskItem(
      id: 'enroll_26',
      type: 'registration',
      title: '26软件1班入学报到',
      body: '入学档案、宿舍、须知与证件照。',
    );
  }

  Profile _profileFields() {
    return _profile;
  }

  List<FieldSource> _prefill(List<FieldSource> extra) {
    final base = <FieldSource>[
      if (_profile.studentNo != null)
        FieldSource(field: 'student_no', label: '学号', value: _profile.studentNo!, source: 'profile'),
      FieldSource(field: 'name', label: '姓名', value: _profile.name, source: 'profile'),
      if (_profile.college != null)
        FieldSource(field: 'college', label: '学院', value: _profile.college!, source: 'profile'),
      if (_profile.className != null)
        FieldSource(field: 'class', label: '班级', value: _profile.className!, source: 'profile'),
      if (_profile.counselorName != null)
        FieldSource(field: 'counselor', label: '辅导员', value: _profile.counselorName!, source: 'profile'),
      if (_profile.phone != null)
        FieldSource(field: 'phone', label: '联系方式', value: _profile.phone!, source: 'profile'),
    ];
    return [...base, ...extra];
  }

  @override
  Future<bool> pingHealth() async => true;

  @override
  Future<LoginResult> login(String username, String password) async {
    throw const ApiException(
      code: 'demo',
      message: '当前是本地预览，无需账号密码。请在登录页选择「预览界面」。',
    );
  }

  @override
  Future<User> me() async => _user;

  @override
  Future<Profile> getProfile() async => _profileFields();

  @override
  Future<Profile> patchProfile(Map<String, dynamic> patch) async {
    _profile = _profile.copyWith(
      phone: patch['phone'] as String? ?? _profile.phone,
      email: patch['email'] as String? ?? _profile.email,
      dorm: patch['dorm'] as String? ?? _profile.dorm,
      bed: patch['bed'] as String? ?? _profile.bed,
    );
    return _profile;
  }

  @override
  Future<void> authorize({
    required String purpose,
    required List<String> fields,
    required String refType,
    String? refId,
  }) async {
    _profile = _profile.copyWith(
      authorizedFields: {..._profile.authorizedFields, ...fields},
    );
  }

  @override
  Future<AskResult> ask({
    required String text,
    List<String> attachmentIds = const [],
    Map<String, String>? slots,
  }) async {
    final q = text.trim();
    final lower = q.replaceAll(' ', '');

    if (lower.contains('困难认定') && (lower.contains('内部') || lower.contains('细则'))) {
      return AskResult(
        conversationId: _id('conv'),
        intent: 'knowledge',
        conclusion: '该规定需辅导员查看。系统不会展示无权限正文，也不会以打码方式泄露条款。',
        permissionDenied: true,
        humanEntry: const HumanEntry(type: 'counselor', label: '转给辅导员'),
      );
    }

    if (lower.contains('励志') || lower.contains('奖学金') || lower.contains('奖助')) {
      if (_user.id == 'stu_liu') {
        return const AskResult(
          conversationId: 'conv_aid',
          intent: 'aid',
          conclusion: '根据已授权的成绩与困难认定，你可能符合国家励志奖学金申请条件。系统只做预审提醒，不会自动提交。',
          citations: [citeAid],
          action: AnswerAction(type: 'aid', label: '查看并生成草稿', ref: {'id': 'aid_lizhi'}),
        );
      }
      return const AskResult(
        conversationId: 'conv_aid_no',
        intent: 'aid',
        conclusion: '按《本科生国家励志奖学金评审办法》第四条，申请需上一学年成绩位于本专业前30%，并完成家庭经济困难认定。当前档案尚未满足或未完成必要授权，暂不推送资格提醒。完成成绩与困难认定授权后可重新预审。',
        citations: [citeAid],
        humanEntry: HumanEntry(type: 'counselor', label: '问辅导员'),
      );
    }

    if (lower.contains('请假') ||
        lower.contains('假条') ||
        lower.contains('医院') ||
        lower.contains('病例') ||
        lower.contains('销假')) {
      if (lower.contains('销假')) {
        return AskResult(
          conversationId: _id('conv'),
          intent: 'leave_return',
          conclusion: '假期期满须在返校当日办理销假。若你有已批准的请假，可直接去确认返校。',
          citations: const [citeLeave2026Return],
          action: _leaves.values.any((l) => l.status == 'pending_return')
              ? AnswerAction(
                  type: 'leave_return',
                  label: '去销假',
                  ref: {'id': _leaves.values.firstWhere((l) => l.status == 'pending_return').id},
                )
              : null,
          humanEntry: const HumanEntry(type: 'counselor', label: '问辅导员'),
        );
      }
      return const AskResult(
        conversationId: 'conv_leave',
        intent: 'leave',
        conclusion: '可以请假。不足一个自然日且不跨天、不影响已登记考试的，由辅导员审批；跨天或与考试/课堂冲突的须加签。材料不全会当场拦住。新旧规定不一致时，以《学生请假管理办法》2026学年秋季学期第十二条为准。',
        citations: [citeLeave2026, citeLeave2025],
        conflicts: [leaveConflict],
        action: AnswerAction(type: 'leave', label: '去请假'),
      );
    }

    if (lower.contains('报到') || lower.contains('入学') || lower.contains('宿舍') || lower.contains('须知')) {
      return const AskResult(
        conversationId: 'conv_enroll',
        intent: 'registration',
        conclusion: '新生须在 11 月 15 日前完成档案核对、宿舍床位确认，并阅读入学须知后确认。未完成的关键项会出现在待办里。',
        citations: [citeEnroll],
        action: AnswerAction(type: 'task', label: '去看报到待办', ref: {'id': 'task_enroll_read'}),
      );
    }

    if (lower.contains('猫') || lower.contains('宠物') || lower.contains('狗')) {
      return AskResult(
        conversationId: _id('conv'),
        intent: 'knowledge',
        conclusion: '知识库中没有找到相关规定，无法判断能否在宿舍饲养宠物。系统不会编造条款。',
        humanEntry: const HumanEntry(type: 'counselor', label: '转给辅导员或宿舍管理窗口'),
      );
    }

    return AskResult(
      conversationId: _id('conv'),
      intent: 'knowledge',
      conclusion: '知识库中没有找到与「$q」直接对应的规定，不能编造答案。你可以换一种问法，或转给辅导员。',
      humanEntry: const HumanEntry(type: 'counselor', label: '转给辅导员'),
    );
  }

  @override
  Future<AttachmentInfo> uploadAttachment(String path, {String? filename, String? kind}) async {
    final item = AttachmentInfo(
      id: _id('att'),
      filename: filename ?? path.split('/').last,
      localPath: path,
      kind: kind,
      expiresAt: DateTime.now().add(const Duration(days: 7)),
    );
    _attachments.insert(0, item);
    return item;
  }

  @override
  Future<DocumentChunk> getChunk(String documentId, String chunkId) async {
    final key = '$documentId::$chunkId';
    if (key == internalChunkKey || documentId == 'doc_internal') {
      throw const ApiException(
        code: 'need_counselor',
        message: '该规定需辅导员查看。系统不会展示无权限正文。',
        status: 403,
      );
    }
    final chunk = chunkTexts[key];
    if (chunk == null) {
      throw const ApiException(code: 'not_found', message: '未找到该条款原文。', status: 404);
    }
    return chunk;
  }

  @override
  Future<List<TodoItem>> todos({String? status}) async => List.of(_todos);

  @override
  Future<ReminderBundle> reminders() async =>
      ReminderBundle(items: List.of(_reminders), mutedCategories: Set.of(_muted));

  @override
  Future<void> muteReminderCategory(String cat, {bool muted = true}) async {
    if (_user.role == UserRole.counselor && cat == 'anomaly') {
      throw const ApiException(code: 'forbidden', message: '辅导员不可关闭本班异常提醒。');
    }
    if (muted) {
      _muted.add(cat);
    } else {
      _muted.remove(cat);
    }
  }

  @override
  Future<LeaveRecord> createLeave({
    String? text,
    List<String> attachmentIds = const [],
    Map<String, dynamic>? fields,
  }) async {
    final reason = (fields?['reason'] as String?) ?? text ?? '';
    final dest = fields?['destination'] as String? ?? '';
    DateTime? start = DateTime.tryParse('${fields?['start_at'] ?? ''}');
    DateTime? end = DateTime.tryParse('${fields?['end_at'] ?? ''}');
    start ??= DateTime(2026, 11, 11, 8);
    end ??= DateTime(2026, 11, 11, 12);
    final crossDay = start.year != end.year || start.month != end.month || start.day != end.day;
    final hours = end.difference(start).inMinutes / 60.0;
    final durationText = crossDay
        ? '${end.difference(start).inDays + 1} 天（跨天）'
        : (hours <= 24 ? '${hours.toStringAsFixed(hours.truncateToDouble() == hours ? 0 : 1)} 小时（短假，不跨天）' : '1 个自然日');
    final atts = _attachments.where((a) => attachmentIds.contains(a.id)).toList();
    final isSick = reason.contains('病') || reason.contains('医院') || reason.contains('就医') || (text ?? '').contains('医院');
    final missing = <MissingItem>[];
    if (reason.trim().isEmpty) {
      missing.add(const MissingItem(field: 'reason', message: '请填写请假原因'));
    }
    if (crossDay && isSick && atts.isEmpty) {
      missing.add(const MissingItem(
        field: 'attachment',
        message: '跨天病假需要病例或诊断证明，当前只有文字说明。',
      ));
    }
    final approvers = <ApproverInfo>[
      const ApproverInfo(name: '王雨晨', role: '辅导员', order: 1, status: 'pending'),
    ];
    String? conflictNote = '未发现已登记考试冲突记录，请自行确认。';
    if (crossDay) {
      approvers.add(const ApproverInfo(name: '辅导员终审并备案', role: '年级负责人（缺省）', order: 2, status: 'pending'));
      conflictNote = '$conflictNote 本次为跨天请假，须加签。本演示环境没有年级负责人，由辅导员终审并备案。';
    }
    final id = _id('leave');
    final record = LeaveRecord(
      id: id,
      status: missing.isEmpty ? 'pending_confirm' : 'draft',
      reason: reason,
      destination: dest,
      startAt: start,
      endAt: end,
      durationText: durationText,
      fields: _prefill([
        FieldSource(field: 'reason', label: '原因', value: reason, source: 'manual'),
        FieldSource(
          field: 'time',
          label: '起止时间',
          value: '${_fmt(start)} 至 ${_fmt(end)}',
          source: 'manual',
        ),
        if (dest.isNotEmpty) FieldSource(field: 'destination', label: '去向', value: dest, source: 'manual'),
      ]),
      attachments: atts,
      approvers: approvers,
      citations: const [citeLeave2026, citeLeave2025],
      validation: ValidationResult(
        ok: missing.isEmpty,
        missing: missing,
        message: missing.isEmpty ? null : '材料不全，已当场拦住，尚未生成可提交单据。',
      ),
      conflictNote: conflictNote,
      legalNote: '提交后，审批前可以撤回；进入审批后需联系审批人退回。系统不会代替你确认，也不会代替老师审批。',
      reusable: _attachments.where((a) => !a.expired).toList(),
    );
    _leaves[id] = record;
    if (missing.isNotEmpty) {
      throw ApiException(
        code: 'validation_blocked',
        message: record.validation.message ?? '材料不全，已当场拦住。',
        details: {
          'missing': missing.map((m) => {'field': m.field, 'message': m.message}).toList(),
          'leave_id': id,
        },
      );
    }
    return record;
  }

  String _fmt(DateTime d) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}';
  }

  @override
  Future<LeaveRecord> extractLeave(String id) async {
    final cur = await getLeave(id);
    final updated = LeaveRecord(
      id: cur.id,
      status: cur.status,
      reason: cur.reason?.isNotEmpty == true ? cur.reason : '医院就诊（从照片识别，请核对）',
      destination: cur.destination?.isNotEmpty == true ? cur.destination : '校医院',
      startAt: cur.startAt ?? DateTime(2026, 11, 11, 8),
      endAt: cur.endAt ?? DateTime(2026, 11, 11, 12),
      durationText: cur.durationText ?? '4 小时（短假，不跨天）',
      fields: cur.fields
          .map((f) => f.field == 'reason' && f.value.isEmpty
              ? const FieldSource(field: 'reason', label: '原因', value: '医院就诊（从照片识别，请核对）', source: 'extracted')
              : f)
          .toList(),
      attachments: cur.attachments,
      approvers: cur.approvers,
      citations: cur.citations,
      validation: cur.validation,
      conflictNote: cur.conflictNote,
      legalNote: cur.legalNote,
      reusable: cur.reusable,
    );
    _leaves[id] = updated;
    return updated;
  }

  @override
  Future<LeaveRecord> getLeave(String id) async {
    final v = _leaves[id];
    if (v == null) {
      throw const ApiException(code: 'not_found', message: '未找到该请假单。', status: 404);
    }
    return v;
  }

  @override
  Future<LeaveRecord> confirmLeave(String id, {Map<String, dynamic>? fields}) async {
    final cur = await getLeave(id);
    if (!cur.validation.ok) {
      throw ApiException(
        code: 'validation_blocked',
        message: cur.validation.message ?? '校验未通过，不能提交。',
        details: {'missing': cur.validation.missing.map((m) => {'field': m.field, 'message': m.message}).toList()},
      );
    }
    final next = LeaveRecord(
      id: cur.id,
      status: 'approving',
      reason: cur.reason,
      destination: cur.destination,
      startAt: cur.startAt,
      endAt: cur.endAt,
      durationText: cur.durationText,
      fields: cur.fields,
      attachments: cur.attachments,
      approvers: cur.approvers,
      citations: cur.citations,
      validation: cur.validation,
      conflictNote: cur.conflictNote,
      legalNote: cur.legalNote,
      reusable: cur.reusable,
    );
    _leaves[id] = next;
    _applications.insert(
      0,
      ApplicationItem(
        id: id,
        kind: 'leave',
        title: '请假 ${cur.durationText ?? ''}',
        status: 'approving',
        updatedAt: DateTime.now(),
        refId: id,
      ),
    );
    _todos.removeWhere((t) => t.refId == id && t.type == 'leave_confirm');
    return next;
  }

  @override
  Future<void> withdrawLeave(String id) async {
    final cur = await getLeave(id);
    if (cur.status != 'submitted' && cur.status != 'pending_confirm' && cur.status != 'approving' && cur.status != 'draft') {
      // still allow before approval finishes in demo if not approved
    }
    if (cur.status == 'approved' || cur.status == 'pending_return') {
      throw const ApiException(code: 'forbidden', message: '已进入批准状态，不能自行撤回，请联系审批人退回。');
    }
    _leaves[id] = LeaveRecord(
      id: cur.id,
      status: 'withdrawn',
      reason: cur.reason,
      destination: cur.destination,
      startAt: cur.startAt,
      endAt: cur.endAt,
      durationText: cur.durationText,
      fields: cur.fields,
      attachments: cur.attachments,
      approvers: cur.approvers,
      citations: cur.citations,
      validation: cur.validation,
      conflictNote: cur.conflictNote,
      legalNote: cur.legalNote,
      reusable: cur.reusable,
    );
  }

  @override
  Future<LeaveRecord> returnLeave(String id, {DateTime? returnedAt}) async {
    final cur = await getLeave(id);
    final next = LeaveRecord(
      id: cur.id,
      status: 'expired',
      reason: cur.reason,
      destination: cur.destination,
      startAt: cur.startAt,
      endAt: cur.endAt,
      durationText: cur.durationText,
      fields: [
        ...cur.fields,
        FieldSource(
          field: 'returned_at',
          label: '返校时间',
          value: _fmt(returnedAt ?? cur.endAt ?? DateTime.now()),
          source: 'manual',
        ),
      ],
      attachments: cur.attachments,
      approvers: cur.approvers,
      citations: cur.citations,
      validation: const ValidationResult(ok: true),
      legalNote: '销假已确认。',
      reusable: cur.reusable,
    );
    _leaves[id] = next;
    _todos.removeWhere((t) => t.refId == id);
    _reminders.removeWhere((r) => r.action?.refId == id);
    return next;
  }

  @override
  Future<List<ApprovalItem>> approvals({String? type}) async => List.of(_approvals);

  @override
  Future<void> decideApproval(String id, {required String decision, String? comment}) async {
    if (decision == 'reject' && (comment == null || comment.trim().isEmpty)) {
      throw const ApiException(code: 'validation_blocked', message: '驳回必须填写原因。');
    }
    final idx = _approvals.indexWhere((a) => a.id == id);
    if (idx < 0) {
      throw const ApiException(code: 'not_found', message: '未找到该审批。', status: 404);
    }
    final cur = _approvals[idx];
    final status = decision == 'approve' ? 'approved' : (decision == 'transfer' ? 'transferred' : 'rejected');
    _approvals[idx] = ApprovalItem(
      id: cur.id,
      type: cur.type,
      title: cur.title,
      applicantName: cur.applicantName,
      summary: cur.summary,
      submittedAt: cur.submittedAt,
      status: status,
      leave: cur.leave,
      citations: cur.citations,
      attachments: cur.attachments,
      validation: cur.validation,
      fields: cur.fields,
    );
    _todos.removeWhere((t) => t.refId == id);
  }

  @override
  Future<List<AidMatch>> aidMatches() async {
    if (_user.id != 'stu_liu') return const [];
    return [
      AidMatch(
        programId: 'aid_lizhi',
        title: '国家励志奖学金',
        reason: '上一学年成绩位于本专业前 30%，且困难认定结果为通过。',
        citations: [citeAid],
        dueAt: DateTime(2026, 12, 5),
      ),
    ];
  }

  @override
  Future<AidDraft> createAidDraft(String programId) async {
    final hasGrade = _profile.authorizedFields.contains('grades');
    final hasHardship = _profile.authorizedFields.contains('hardship');
    final fields = _prefill([
      FieldSource(
        field: 'grades',
        label: '成绩排名',
        value: hasGrade ? '本专业前 30%（已授权）' : '',
        source: hasGrade ? 'profile' : 'unauthorized',
      ),
      FieldSource(
        field: 'hardship',
        label: '困难认定',
        value: hasHardship ? '通过（已授权）' : '',
        source: hasHardship ? 'profile' : 'unauthorized',
      ),
      FieldSource(
        field: 'bank',
        label: '银行卡',
        value: '',
        source: 'unauthorized',
      ),
      const FieldSource(field: 'statement', label: '个人陈述', value: '', source: 'manual'),
    ]);
    final draft = AidDraft(
      id: _id('draft'),
      programId: programId,
      title: '国家励志奖学金申请草稿',
      status: 'draft',
      fields: fields,
      citations: const [citeAid],
    );
    _drafts[draft.id] = draft;
    return draft;
  }

  @override
  Future<AidDraft> getAidDraft(String id) async {
    if (id == 'aid_lizhi' && !_drafts.containsKey(id)) {
      final created = await createAidDraft('aid_lizhi');
      _drafts['aid_lizhi'] = created;
      return created;
    }
    final v = _drafts[id];
    if (v == null) {
      throw const ApiException(code: 'not_found', message: '未找到该草稿。', status: 404);
    }
    return v;
  }

  @override
  Future<AidDraft> confirmAidDraft(String id, {Map<String, dynamic>? fields}) async {
    final cur = await getAidDraft(id);
    final next = AidDraft(
      id: cur.id,
      programId: cur.programId,
      title: cur.title,
      status: 'confirmed_pending_submit',
      fields: cur.fields,
      attachments: cur.attachments,
      citations: cur.citations,
      validation: cur.validation,
      packageDownloadUrl: 'demo://package/$id',
      statement: fields?['statement'] as String? ?? cur.statement,
    );
    _drafts[id] = next;
    _applications.insert(
      0,
      ApplicationItem(
        id: id,
        kind: 'aid',
        title: cur.title,
        status: 'confirmed_pending_submit',
        updatedAt: DateTime.now(),
        refId: id,
      ),
    );
    return next;
  }

  @override
  Future<TaskItem> getTask(String id) async {
    final v = _tasks[id];
    if (v == null) {
      throw const ApiException(code: 'not_found', message: '未找到该任务。', status: 404);
    }
    return v;
  }

  @override
  Future<TaskItem> submitTask(
    String id, {
    String? note,
    List<String> attachmentIds = const [],
    Map<String, dynamic>? fields,
  }) async {
    final cur = await getTask(id);
    if (cur.signupValidation != null && !cur.signupValidation!.ok) {
      throw ApiException(
        code: 'validation_blocked',
        message: cur.signupValidation!.message ?? '不符合条件，不能提交。',
        details: {
          'missing': cur.signupValidation!.missing
              .map((m) => {'field': m.field, 'message': m.message})
              .toList(),
        },
      );
    }
    final next = TaskItem(
      id: cur.id,
      type: cur.type,
      title: cur.title,
      body: cur.body,
      dueAt: cur.dueAt,
      audience: cur.audience,
      submitMode: cur.submitMode,
      citations: cur.citations,
      status: 'submitted',
      capacity: cur.capacity,
      signedUp: (cur.signedUp ?? 0) + (cur.type == 'volunteer' ? 1 : 0),
      requirements: cur.requirements,
      prefills: cur.prefills,
      location: cur.location,
      timeText: cur.timeText,
      needReview: cur.needReview,
    );
    _tasks[id] = next;
    _todos.removeWhere((t) => t.refId == id);
    return next;
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
    final id = _id('task');
    final task = TaskItem(
      id: id,
      type: type,
      title: title,
      body: body,
      dueAt: dueAt,
      audience: audience,
      submitMode: extra?['submit_mode'] as String?,
      location: extra?['location'] as String?,
      timeText: extra?['time_text'] as String?,
      capacity: extra?['capacity'] is int ? extra!['capacity'] as int : null,
      needReview: extra?['need_review'] == true,
    );
    _tasks[id] = task;
    _progress[id] = TaskProgress(taskId: id, title: title, total: 0, completed: 0);
    _todos.insert(
      0,
      TodoItem(
        id: 'td_$id',
        type: type,
        title: title,
        subtitle: '已发布 · $audience',
        dueAt: dueAt,
        actionLabel: '看进度',
        actionType: 'progress',
        refType: 'task',
        refId: id,
      ),
    );
    return task;
  }

  @override
  Future<TaskProgress> taskProgress(String id) async {
    final v = _progress[id];
    if (v == null) {
      final task = _tasks[id];
      return TaskProgress(taskId: id, title: task?.title, total: 0, completed: 0);
    }
    return v;
  }

  @override
  Future<List<ApplicationItem>> myApplications() async => List.of(_applications);

  @override
  Future<List<AttachmentInfo>> myAttachments() async => List.of(_attachments);
}
