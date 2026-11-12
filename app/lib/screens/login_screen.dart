import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config/app_config.dart';
import '../config/demo_accounts.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _originCtrl = TextEditingController();
  bool _busy = false;
  bool _showServer = false;
  String? _healthText;
  bool? _healthOk;

  @override
  void initState() {
    super.initState();
    final session = context.read<Session>();
    _originCtrl.text = session.origin;
    WidgetsBinding.instance.addPostFrameCallback((_) => _ping());
  }

  @override
  void dispose() {
    _userCtrl.dispose();
    _passCtrl.dispose();
    _originCtrl.dispose();
    super.dispose();
  }

  Future<void> _ping() async {
    final session = context.read<Session>();
    await session.setOrigin(_originCtrl.text);
    final ok = await session.checkHealth();
    if (!mounted) return;
    setState(() {
      _healthOk = ok;
      _healthText = ok ? '服务器可访问' : '暂时连不上服务器（API 可能尚未对外）。可先用本地预览走界面。';
    });
  }

  Future<void> _login() async {
    final u = _userCtrl.text.trim();
    final p = _passCtrl.text;
    if (u.isEmpty || p.isEmpty) {
      _toast('请输入账号和密码。登录页不预填口令。');
      return;
    }
    setState(() => _busy = true);
    try {
      await context.read<Session>().setOrigin(_originCtrl.text);
      await context.read<Session>().login(u, p);
    } on ApiException catch (e) {
      _toast(e.message);
    } catch (e) {
      _toast('登录失败：$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _preview(String role) async {
    setState(() => _busy = true);
    try {
      await context.read<Session>().enterDemo(role);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 48, 24, 24),
          children: [
            const Text(AppConfig.appFullName, style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, height: 1.25)),
            const SizedBox(height: 8),
            const Text('师生共用 · 少填、少跑、少猜', style: TextStyle(color: AppColors.muted, fontSize: 15)),
            const SizedBox(height: 32),
            TextField(
              controller: _userCtrl,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.username],
              decoration: const InputDecoration(labelText: '学号 / 工号', hintText: '请输入账号'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passCtrl,
              obscureText: true,
              onSubmitted: (_) => _login(),
              decoration: const InputDecoration(labelText: '密码', hintText: '请输入密码'),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _login,
              child: _busy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('登录'),
            ),
            const SizedBox(height: 16),
            TextButton(
              onPressed: () => setState(() => _showServer = !_showServer),
              child: Text(_showServer ? '收起服务器设置' : '服务器：${_originCtrl.text}'),
            ),
            if (_showServer) ...[
              TextField(
                controller: _originCtrl,
                decoration: const InputDecoration(
                  labelText: '服务器地址',
                  hintText: 'http://8.148.186.220',
                  helperText: '默认指向演示 ECS。业务接口在 /api/v1，健康检查为 /health。',
                ),
              ),
              const SizedBox(height: 8),
              OutlinedButton(onPressed: _ping, child: const Text('检查连接')),
            ],
            if (_healthText != null) ...[
              const SizedBox(height: 8),
              Text(
                _healthText!,
                style: TextStyle(color: _healthOk == true ? AppColors.success : AppColors.muted, height: 1.4),
              ),
            ],
            const SizedBox(height: 28),
            const Text('演示账号', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            const Text(
              '口令来自仓库 docs/DEMO_ACCOUNTS.md，点一项会填入登录框，仍需点登录。连不上服务器时请用下方本地预览。',
              style: TextStyle(color: AppColors.muted, height: 1.4, fontSize: 13),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final a in DemoAccounts.appUsers)
                  OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () {
                            setState(() {
                              _userCtrl.text = a.username;
                              _passCtrl.text = DemoAccounts.password;
                            });
                          },
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(0, 40),
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                    ),
                    child: Text(a.label),
                  ),
              ],
            ),
            const SizedBox(height: 28),
            const Text('本地预览界面', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            const Text(
              '不连接服务器、不使用真实密码，仅用本地演示数据走通主要页面。',
              style: TextStyle(color: AppColors.muted, height: 1.4, fontSize: 13),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _roleChip('学生（新生）', 'freshman'),
                _roleChip('学生（在校）', 'senior'),
                _roleChip('任课教师', 'teacher'),
                _roleChip('辅导员', 'counselor'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _roleChip(String label, String key) {
    return OutlinedButton(
      onPressed: _busy ? null : () => _preview(key),
      style: OutlinedButton.styleFrom(minimumSize: const Size(0, 40), padding: const EdgeInsets.symmetric(horizontal: 12)),
      child: Text(label),
    );
  }
}
