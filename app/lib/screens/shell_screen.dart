import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import 'approvals_screen.dart';
import 'applications_screen.dart';
import 'home_screen.dart';
import 'profile_screen.dart';
import 'publish_task_screen.dart';
import 'reminders_screen.dart';

class ShellScreen extends StatefulWidget {
  const ShellScreen({super.key});

  @override
  State<ShellScreen> createState() => _ShellScreenState();
}

class _Tab {
  const _Tab(this.label, this.icon, this.builder);
  final String label;
  final IconData icon;
  final WidgetBuilder builder;
}

class _ShellScreenState extends State<ShellScreen> {
  int _index = 0;

  List<_Tab> _tabsFor(User? user) {
    if (user?.role == UserRole.teacher || user?.role == UserRole.counselor) {
      return [
        _Tab('首页', Icons.home_outlined, (_) => const HomeScreen()),
        _Tab('审批', Icons.fact_check_outlined, (_) => const ApprovalsScreen()),
        _Tab('发布', Icons.campaign_outlined, (_) => const PublishTaskScreen()),
        _Tab('我的', Icons.person_outline, (_) => const ProfileScreen()),
      ];
    }
    return [
      _Tab('首页', Icons.home_outlined, (_) => const HomeScreen()),
      _Tab('提醒', Icons.notifications_none, (_) => const RemindersScreen()),
      _Tab('申请', Icons.folder_open_outlined, (_) => const ApplicationsScreen()),
      _Tab('我的', Icons.person_outline, (_) => const ProfileScreen()),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final tabs = _tabsFor(session.user);
    final i = _index.clamp(0, tabs.length - 1);
    return Scaffold(
      body: Column(
        children: [
          if (session.demoMode) const DemoBanner(),
          if (!session.demoMode && !session.online) const OfflineBanner(),
          Expanded(child: tabs[i].builder(context)),
        ],
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: AppColors.card,
          border: Border(top: BorderSide(color: AppColors.line)),
        ),
        child: SafeArea(
          child: BottomNavigationBar(
            currentIndex: i,
            onTap: (v) => setState(() => _index = v),
            items: [
              for (final t in tabs) BottomNavigationBarItem(icon: Icon(t.icon), label: t.label),
            ],
          ),
        ),
      ),
    );
  }
}
