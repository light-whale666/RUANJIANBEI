import '../models/models.dart';

const citeLeave2026 = Citation(
  documentId: 'doc_leave_2026',
  chunkId: 'c_leave_12',
  filename: '学生请假管理办法',
  section: '第三章 审批权限',
  article: '第十二条',
  semester: '2026学年秋季学期',
  quote:
      '学生因病、因事请假，不足一个自然日且不跨天、不影响已登记考试的，由辅导员（班主任）审批。跨天或与已登记考试、课堂冲突的，须按本办法加签。',
  isGoverning: true,
);

const citeLeave2026Return = Citation(
  documentId: 'doc_leave_2026',
  chunkId: 'c_leave_18',
  filename: '学生请假管理办法',
  section: '第四章 销假',
  article: '第十八条',
  semester: '2026学年秋季学期',
  quote: '假期期满，学生须在返校当日办理销假。逾期未销假的，按旷课或擅自离校处理。',
  isGoverning: true,
);

const citeLeave2025 = Citation(
  documentId: 'doc_leave_2025',
  chunkId: 'c_leave_old_8',
  filename: '学生请假管理暂行办法',
  section: '第二章',
  article: '第八条',
  semester: '2025学年春季学期',
  quote: '请假一天以内由班主任审批；超过一天须学院办公室加盖公章。',
  isGoverning: false,
);

const citeAid = Citation(
  documentId: 'doc_aid_2026',
  chunkId: 'c_aid_4',
  filename: '本科生国家励志奖学金评审办法',
  section: '第二章 申请条件',
  article: '第四条',
  semester: '2026学年秋季学期',
  quote: '申请国家励志奖学金的学生，应当品学兼优，家庭经济困难，上一学年学习成绩排名位于本专业前30%，且通过家庭经济困难认定。',
  isGoverning: true,
);

const citeEnroll = Citation(
  documentId: 'doc_enroll_2026',
  chunkId: 'c_enroll_3',
  filename: '2026级新生入学须知',
  section: '一、报到安排',
  article: '第3条',
  semester: '2026学年秋季学期',
  quote: '新生须在报到截止日前完成个人档案核对、宿舍床位确认，并阅读本须知后签字确认。未完成关键报到项的，由辅导员跟进。',
  isGoverning: true,
);

const leaveConflict = ConflictNote(
  chosen: '以《学生请假管理办法》2026学年秋季学期第十二条为准',
  other: '《学生请假管理暂行办法》2025学年春季学期第八条（已搁置）',
  reason: '同主题以较新生效学期为准，且后台已将2026年版标记为优先文件。',
);

const chunkTexts = <String, DocumentChunk>{
  'doc_leave_2026::c_leave_12': DocumentChunk(
    documentId: 'doc_leave_2026',
    chunkId: 'c_leave_12',
    filename: '学生请假管理办法',
    section: '第三章 审批权限',
    article: '第十二条',
    semester: '2026学年秋季学期',
    highlight:
        '不足一个自然日且不跨天、不影响已登记考试的，由辅导员（班主任）审批。跨天或与已登记考试、课堂冲突的，须按本办法加签。',
    text:
        '第十二条 学生因病、因事请假，不足一个自然日且不跨天、不影响已登记考试的，由辅导员（班主任）审批。跨天或与已登记考试、课堂冲突的，须按本办法加签。\n\n'
        '与本课考试冲突的，加签任课教师；无课表冲突但跨天的，由辅导员审批，并报年级负责人备案；名单中无年级负责人的，由辅导员终审并备案。\n\n'
        '请假应当提交相应证明材料。跨天病假须提供病例或诊断证明。材料不全的，不得进入审批。',
  ),
  'doc_leave_2026::c_leave_18': DocumentChunk(
    documentId: 'doc_leave_2026',
    chunkId: 'c_leave_18',
    filename: '学生请假管理办法',
    section: '第四章 销假',
    article: '第十八条',
    semester: '2026学年秋季学期',
    highlight: '假期期满，学生须在返校当日办理销假。',
    text:
        '第十八条 假期期满，学生须在返校当日办理销假。逾期未销假的，按旷课或擅自离校处理。\n\n'
        '销假由学生本人确认返校时间，辅导员予以登记。',
  ),
  'doc_leave_2025::c_leave_old_8': DocumentChunk(
    documentId: 'doc_leave_2025',
    chunkId: 'c_leave_old_8',
    filename: '学生请假管理暂行办法',
    section: '第二章',
    article: '第八条',
    semester: '2025学年春季学期',
    highlight: '请假一天以内由班主任审批；超过一天须学院办公室加盖公章。',
    text:
        '第八条 请假一天以内由班主任审批；超过一天须学院办公室加盖公章。\n\n'
        '（本办法已被 2026 年秋季学期新颁布的《学生请假管理办法》取代，仅作对照，不以本稿为准。）',
  ),
  'doc_aid_2026::c_aid_4': DocumentChunk(
    documentId: 'doc_aid_2026',
    chunkId: 'c_aid_4',
    filename: '本科生国家励志奖学金评审办法',
    section: '第二章 申请条件',
    article: '第四条',
    semester: '2026学年秋季学期',
    highlight: '上一学年学习成绩排名位于本专业前30%，且通过家庭经济困难认定。',
    text:
        '第四条 申请国家励志奖学金的学生，应当品学兼优，家庭经济困难，上一学年学习成绩排名位于本专业前30%，且通过家庭经济困难认定。\n\n'
        '符合条件的学生由学校组织申报，不代替学生提交申请。材料应当真实完整。',
  ),
  'doc_enroll_2026::c_enroll_3': DocumentChunk(
    documentId: 'doc_enroll_2026',
    chunkId: 'c_enroll_3',
    filename: '2026级新生入学须知',
    section: '一、报到安排',
    article: '第3条',
    semester: '2026学年秋季学期',
    highlight: '新生须在报到截止日前完成个人档案核对、宿舍床位确认，并阅读本须知后签字确认。',
    text:
        '第3条 新生须在报到截止日前完成个人档案核对、宿舍床位确认，并阅读本须知后签字确认。未完成关键报到项的，由辅导员跟进。\n\n'
        '报到截止日期为 2026 年 11 月 15 日。',
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
