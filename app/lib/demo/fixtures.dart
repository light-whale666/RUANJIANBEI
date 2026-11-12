import '../models/models.dart';

const _watermark = '【模板】请替换为学校正式文件，本文不是任何学校的正式校规。';

const citeLeave2026 = Citation(
  documentId: 'doc_leave_example',
  chunkId: 'c_leave_2',
  filename: '【模板示例】学生请假管理规定',
  section: '第二条',
  article: '第二条 【示例】短假',
  semester: '【示例】2025-2026学年',
  quote:
      '$_watermark【示例】短假是指不超过 1 个自然日且不跨天、且不影响已登记考试的请假，由辅导员审批。本句为模板示例，用于演示检索，不是任何学校的正式校规。',
  isGoverning: true,
);

const citeLeave2026Return = Citation(
  documentId: 'doc_leave_example',
  chunkId: 'c_leave_5',
  filename: '【模板示例】学生请假管理规定',
  section: '第五条',
  article: '第五条 【示例】销假',
  semester: '【示例】2025-2026学年',
  quote: '$_watermark【示例】批准后学生须在假期结束返校并办理销假。本句为模板示例，不是任何学校的正式校规。',
  isGoverning: true,
);

const citeLeave2025 = Citation(
  documentId: 'doc_leave_example_old',
  chunkId: 'c_leave_old_2',
  filename: '【模板示例】学生请假管理规定（较旧学期）',
  section: '第二条',
  article: '第二条 【示例】短假',
  semester: '【示例】2024-2025学年',
  quote: '$_watermark【示例】本条为较旧学期模板示例，仅作对照，不以本稿为准。',
  isGoverning: false,
);

const citeAid = Citation(
  documentId: 'doc_aid_example',
  chunkId: 'c_aid_2',
  filename: '【模板示例】奖助学金实施办法',
  section: '第二条',
  article: '第二条 【示例】学业条件',
  semester: '【示例】2025-2026学年',
  quote: '$_watermark【示例】申请学生学习成绩优秀，平均学分绩点（GPA）不低于 3.0。本句为模板示例，用于演示检索，不是任何学校的正式校规。',
  isGoverning: true,
);

const citeEnroll = Citation(
  documentId: 'doc_enroll_2025_example',
  chunkId: 'c_enroll_3',
  filename: '【模板示例】报到入学须知-2025秋',
  section: '第三条',
  article: '第三条 【示例】宿舍入住',
  semester: '【示例】2025-2026学年秋季',
  quote: '$_watermark【示例】新生须在报到当天 【示例】20:00 前到宿舍办理入住。该时间为模板示例，不是任何学校公布的正式截止时间。',
  isGoverning: true,
);

const citeEnrollOld = Citation(
  documentId: 'doc_enroll_2024_example',
  chunkId: 'c_enroll_3_old',
  filename: '【模板示例】报到入学须知-2024秋',
  section: '第三条',
  article: '第三条 【示例】宿舍入住',
  semester: '【示例】2024-2025学年秋季',
  quote: '$_watermark【示例】新生须在报到当天 【示例】17:00 前到宿舍办理入住。该时间为模板示例，用于演示冲突裁决，不是任何学校公布的正式截止时间。',
  isGoverning: false,
);

const leaveConflict = ConflictNote(
  chosen: '以【模板示例】报到入学须知-2025秋（【示例】2025-2026学年秋季）为准',
  other: '【模板示例】报到入学须知-2024秋（【示例】2024-2025学年秋季）',
  reason: '同文件以较新生效学期为准。两条均为模板示例时间（【示例】20:00 与【示例】17:00），不是任何学校的正式校规。',
);

const enrollConflict = leaveConflict;

const chunkTexts = <String, DocumentChunk>{
  'doc_leave_example::c_leave_2': DocumentChunk(
    documentId: 'doc_leave_example',
    chunkId: 'c_leave_2',
    filename: '【模板示例】学生请假管理规定',
    section: '第二条',
    article: '第二条 【示例】短假',
    semester: '【示例】2025-2026学年',
    highlight: '【示例】短假是指不超过 1 个自然日且不跨天、且不影响已登记考试的请假，由辅导员审批。',
    text:
        '$_watermark\n【模板示例】下列条款仅用于演示检索，不是任何学校的正式校规。\n\n'
        '第二条 【示例】短假\n【示例】短假是指不超过 1 个自然日且不跨天、且不影响已登记考试的请假，由辅导员审批。本句为模板示例，用于演示检索。',
  ),
  'doc_leave_example::c_leave_5': DocumentChunk(
    documentId: 'doc_leave_example',
    chunkId: 'c_leave_5',
    filename: '【模板示例】学生请假管理规定',
    section: '第五条',
    article: '第五条 【示例】销假',
    semester: '【示例】2025-2026学年',
    highlight: '【示例】批准后学生须在假期结束返校并办理销假。',
    text:
        '$_watermark\n\n第五条 【示例】销假\n【示例】批准后学生须在假期结束返校并办理销假。本句为模板示例。',
  ),
  'doc_leave_example_old::c_leave_old_2': DocumentChunk(
    documentId: 'doc_leave_example_old',
    chunkId: 'c_leave_old_2',
    filename: '【模板示例】学生请假管理规定（较旧学期）',
    section: '第二条',
    article: '第二条 【示例】短假',
    semester: '【示例】2024-2025学年',
    highlight: '【示例】本条为较旧学期模板示例，仅作对照，不以本稿为准。',
    text:
        '$_watermark\n\n第二条 【示例】短假\n【示例】本条为较旧学期模板示例，仅作对照，不以本稿为准。',
  ),
  'doc_aid_example::c_aid_2': DocumentChunk(
    documentId: 'doc_aid_example',
    chunkId: 'c_aid_2',
    filename: '【模板示例】奖助学金实施办法',
    section: '第二条',
    article: '第二条 【示例】学业条件',
    semester: '【示例】2025-2026学年',
    highlight: '【示例】平均学分绩点（GPA）不低于 3.0。',
    text:
        '$_watermark\n【模板示例】下列条款仅用于演示检索，不是任何学校的正式校规。\n\n'
        '第二条 【示例】学业条件\n【示例】申请学生学习成绩优秀，平均学分绩点（GPA）不低于 3.0。本句为模板示例，用于演示检索。',
  ),
  'doc_enroll_2025_example::c_enroll_3': DocumentChunk(
    documentId: 'doc_enroll_2025_example',
    chunkId: 'c_enroll_3',
    filename: '【模板示例】报到入学须知-2025秋',
    section: '第三条',
    article: '第三条 【示例】宿舍入住',
    semester: '【示例】2025-2026学年秋季',
    highlight: '【示例】新生须在报到当天 【示例】20:00 前到宿舍办理入住。',
    text:
        '$_watermark\n【模板示例】下列条款仅用于演示检索与冲突裁决，不是任何学校的正式校规。\n\n'
        '第三条 【示例】宿舍入住\n【示例】新生须在报到当天 【示例】20:00 前到宿舍办理入住。该时间为模板示例，不是任何学校公布的正式截止时间。',
  ),
  'doc_enroll_2024_example::c_enroll_3_old': DocumentChunk(
    documentId: 'doc_enroll_2024_example',
    chunkId: 'c_enroll_3_old',
    filename: '【模板示例】报到入学须知-2024秋',
    section: '第三条',
    article: '第三条 【示例】宿舍入住',
    semester: '【示例】2024-2025学年秋季',
    highlight: '【示例】新生须在报到当天 【示例】17:00 前到宿舍办理入住。',
    text:
        '$_watermark\n【模板示例】下列条款仅用于演示检索与冲突裁决，不是任何学校的正式校规。\n\n'
        '第三条 【示例】宿舍入住\n【示例】新生须在报到当天 【示例】17:00 前到宿舍办理入住。该时间为模板示例，用于演示冲突裁决，不是任何学校公布的正式截止时间。',
  ),
};

const internalChunkKey = 'doc_internal::c_hardship_2';

User freshmanUser() => const User(
      id: 'stu_chen',
      username: '2026210101',
      name: '陈晓桐',
      role: UserRole.student,
      isFreshman: true,
      college: '计算机学院',
      className: '26软件1班',
      studentNo: '2026210101',
    );

User seniorUser() => const User(
      id: 'stu_liu',
      username: '2023210108',
      name: '刘振宇',
      role: UserRole.student,
      isFreshman: false,
      college: '计算机学院',
      className: '23软件2班',
      studentNo: '2023210108',
    );

User teacherUser() => const User(
      id: 'tea_li',
      username: 'T20230018',
      name: '李承泽',
      role: UserRole.teacher,
      college: '计算机学院',
      staffNo: 'T20230018',
    );

User counselorUser() => const User(
      id: 'cou_wang',
      username: 'C20190007',
      name: '王雨晨',
      role: UserRole.counselor,
      college: '计算机学院',
      staffNo: 'C20190007',
    );

Profile freshmanProfile() => const Profile(
      studentNo: '2026210101',
      name: '陈晓桐',
      college: '计算机学院',
      major: '软件工程',
      grade: '2026级新生',
      className: '26软件1班',
      phone: '13800002101',
      email: 'chenxt@campus.edu',
      counselorName: '王雨晨',
      counselorId: 'cou_wang',
      dorm: '6号楼402',
      bed: '3号床',
      emergencyContacts: [
        EmergencyContact(name: '陈建军', relation: '父亲', phone: '13900008821'),
      ],
    );

Profile seniorProfile() => const Profile(
      studentNo: '2023210108',
      name: '刘振宇',
      college: '计算机学院',
      major: '软件工程',
      grade: '2023级',
      className: '23软件2班',
      phone: '13700002108',
      email: 'liuzy@campus.edu',
      counselorName: '王雨晨',
      counselorId: 'cou_wang',
      dorm: '3号楼217',
      bed: '1号床',
      emergencyContacts: [
        EmergencyContact(name: '刘秀兰', relation: '母亲', phone: '13600007711'),
      ],
      authorizedFields: {'grades', 'hardship'},
    );

Profile teacherProfile() => const Profile(
      staffNo: 'T20230018',
      name: '李承泽',
      college: '计算机学院',
      major: '软件工程',
      phone: '18600000018',
      email: 'licz@campus.edu',
    );

Profile counselorProfile() => const Profile(
      staffNo: 'C20190007',
      name: '王雨晨',
      college: '计算机学院',
      phone: '18600000007',
      email: 'wangyc@campus.edu',
    );


DecisionTrace demoDecision({
  required String path,
  required String intent,
  double confidence = 0.82,
  bool uncertain = false,
  String source = 'rules',
  List<DecisionStep> steps = const [],
  String? whyConfirm,
  String? awaiting,
  List<String> knowledgeScope = const [],
  List<String> used = const [],
  List<String> skipped = const [],
}) {
  return DecisionTrace(
    path: path,
    intent: intent,
    confidence: confidence,
    uncertain: uncertain,
    source: source,
    steps: steps,
    whyConfirm: whyConfirm,
    awaiting: awaiting,
    knowledgeScope: knowledgeScope,
    prefill: PrefillTrace(used: used, skippedUnauthorized: skipped),
  );
}

const whyLeaveConfirm = '生成或提交请假草稿会改动学生办事数据，必须由学生本人核对并确认，系统不会代替确认，也不会自动提交。';
const whyAidConfirm = '奖助预审或生成草稿会使用学生档案并可能改动申请数据，必须由学生本人确认，系统不会自动提交。';
