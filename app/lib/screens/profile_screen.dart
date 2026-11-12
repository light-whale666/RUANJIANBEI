import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config/app_config.dart';
import '../models/models.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Profile? _profile;
  bool _loading = true;
  String? _error;
  final _phone = TextEditingController();
  final _email = TextEditingController();
  final _dorm = TextEditingController();
  final _bed = TextEditingController();
  bool _saving = false;
  bool _showSensitive = false;

  static const _sensitive = {
    'grades': '成绩',
    'hardship': '困难认定',
    'family_economy': '家庭经济情况',
    'bank': '银行卡',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _phone.dispose();
    _email.dispose();
    _dorm.dispose();
    _bed.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final session = context.read<Session>();
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final p = await session.guard(() => session.api.getProfile());
      if (!mounted) return;
      _phone.text = p.phone ?? '';
      _email.text = p.email ?? '';
      _dorm.text = p.dorm ?? '';
      _bed.text = p.bed ?? '';
      setState(() {
        _profile = p;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final p = await context.read<Session>().api.patchProfile({
        'phone': _phone.text.trim(),
        'email': _email.text.trim(),
        'dorm': _dorm.text.trim(),
        'bed': _bed.text.trim(),
      });
      if (!mounted) return;
      setState(() => _profile = p);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已保存可自行维护的联系与宿舍信息。')));
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _authorize(String field) async {
    final purposeCtrl = TextEditingController(text: '奖助或证明预审');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('按这一次办事授权'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('将授权使用「${_sensitive[field]}」。授权只针对这一次办事，不是永久全开放。'),
            const SizedBox(height: 12),
            TextField(controller: purposeCtrl, decoration: const InputDecoration(labelText: '将用于')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('确认授权')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await context.read<Session>().api.authorize(
            purpose: purposeCtrl.text.trim(),
            fields: [field],
            refType: 'profile',
          );
      await _load();
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('我的档案'),
        automaticallyImplyLeading: Navigator.of(context).canPop(),
        actions: [
          IconButton(
            tooltip: '退出',
            onPressed: () => session.logout(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
              children: [
                if (_error != null) ErrorBanner(_error!, onRetry: _load),
                _idCard(session),
                const SizedBox(height: 12),
                const SectionTitle('基础信息（只填一次，用于预填）'),
                SoftCard(
                  child: Column(
                    children: [
                      _readonly('学号 / 工号', _profile?.studentNo ?? _profile?.staffNo ?? session.user?.username),
                      _readonly('姓名', _profile?.name),
                      _readonly('学院', _profile?.college),
                      _readonly('专业', _profile?.major),
                      _readonly('年级', _profile?.grade),
                      _readonly('班级', _profile?.className),
                      _readonly('辅导员', _profile?.counselorName),
                      const Padding(
                        padding: EdgeInsets.only(top: 8),
                        child: Text('学号、姓名、学院专业年级班级由管理员导入。如需更正，请向辅导员申请，避免与名单冲突。', style: TextStyle(color: AppColors.muted, fontSize: 12, height: 1.4)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                const SectionTitle('可自行更新'),
                TextField(controller: _phone, decoration: const InputDecoration(labelText: '手机')),
                const SizedBox(height: 8),
                TextField(controller: _email, decoration: const InputDecoration(labelText: '邮箱')),
                const SizedBox(height: 8),
                TextField(controller: _dorm, decoration: const InputDecoration(labelText: '宿舍')),
                const SizedBox(height: 8),
                TextField(controller: _bed, decoration: const InputDecoration(labelText: '床位')),
                const SizedBox(height: 8),
                if (_profile?.emergencyContacts.isNotEmpty == true)
                  FieldTable(
                    title: '紧急联系人',
                    fields: [
                      for (final e in _profile!.emergencyContacts)
                        FieldSource(field: 'em', label: e.relation, value: '${e.name}  ${e.phone}', source: 'profile'),
                    ],
                  ),
                const SizedBox(height: 12),
                FilledButton(onPressed: _saving ? null : _save, child: const Text('保存')),
                const SizedBox(height: 16),
                SectionTitle(
                  '敏感项（默认不预填）',
                  trailing: TextButton(
                    onPressed: () => setState(() => _showSensitive = !_showSensitive),
                    child: Text(_showSensitive ? '收起' : '展开'),
                  ),
                ),
                if (_showSensitive)
                  SoftCard(
                    child: Column(
                      children: [
                        const Text('银行卡、家庭经济、成绩、困难认定等，需按这一次办事授权后才会用于预审或预填。未授权时确认页会标明「未授权，未使用」。', style: TextStyle(height: 1.45, color: AppColors.muted)),
                        const SizedBox(height: 8),
                        for (final e in _sensitive.entries)
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(e.value),
                            subtitle: Text((_profile?.authorizedFields.contains(e.key) ?? false) ? '已授权（按事项）' : '未授权'),
                            trailing: TextButton(
                              onPressed: () => _authorize(e.key),
                              child: const Text('授权'),
                            ),
                          ),
                      ],
                    ),
                  ),
                const SizedBox(height: 24),
                const SectionTitle('服务器'),
                SoftCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(session.demoMode ? '当前为本地预览' : '当前服务器：${session.origin}'),
                      const SizedBox(height: 6),
                      const Text('业务接口 /api/v1，健康检查 /health。JWT 仅保存在安全存储中。', style: TextStyle(color: AppColors.muted, fontSize: 12, height: 1.4)),
                      const SizedBox(height: 8),
                      Text('版本 ${AppConfig.appName} 1.0.0', style: const TextStyle(color: AppColors.muted, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  Widget _idCard(Session session) {
    return SoftCard(
      color: AppColors.tealDark,
      child: DefaultTextStyle(
        style: const TextStyle(color: Colors.white),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(roleLabel(session.user?.role ?? UserRole.unknown), style: const TextStyle(color: Color(0xFFB9E0D8))),
            const SizedBox(height: 6),
            Text(session.user?.name ?? '', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text(session.user?.className ?? session.user?.college ?? ''),
          ],
        ),
      ),
    );
  }

  Widget _readonly(String label, String? value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(width: 86, child: Text(label, style: const TextStyle(color: AppColors.muted))),
          Expanded(child: Text(value?.isNotEmpty == true ? value! : '—')),
        ],
      ),
    );
  }
}
