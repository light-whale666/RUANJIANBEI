/// 演示登录名与口令，来源：仓库 `docs/DEMO_ACCOUNTS.md`。
/// 只用于演示登录，不是服务器数据库、MinIO 或其它基础设施密钥。
class DemoAccount {
  const DemoAccount({
    required this.username,
    required this.label,
    required this.role,
  });

  final String username;
  final String label;
  final String role;
}

class DemoAccounts {
  /// 与 docs/DEMO_ACCOUNTS.md 保持一致。
  static const password = 'CampusDemo@2026';

  /// App 前台可用的演示账号（admin 仅管理端，不在此列出）。
  static const appUsers = <DemoAccount>[
    DemoAccount(username: 'stu.chen', label: '陈晓（新生）', role: '学生'),
    DemoAccount(username: 'stu.lin', label: '林雨（在校，可能符合奖助）', role: '学生'),
    DemoAccount(username: 'stu.zhao', label: '赵强（在校，不够格不推奖助）', role: '学生'),
    DemoAccount(username: 'teacher.li', label: '李老师（高等数学）', role: '任课教师'),
    DemoAccount(username: 'teacher.zhang', label: '张老师（大学英语）', role: '任课教师'),
    DemoAccount(username: 'counselor.wang', label: '王敏（辅导员）', role: '辅导员'),
  ];
}
