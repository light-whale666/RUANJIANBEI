import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../widgets/ui.dart';

class RemindersScreen extends StatefulWidget {
  const RemindersScreen({super.key});

  @override
  State<RemindersScreen> createState() => _RemindersScreenState();
}

class _RemindersScreenState extends State<RemindersScreen> {
  ReminderBundle _bundle = const ReminderBundle();
  bool _loading = true;
  String? _error;

  static const cats = [
    ('deadline', '时限'),
    ('eligibility', '资格'),
    ('anomaly', '异常'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final b = await context.read<Session>().api.reminders();
      if (!mounted) return;
      setState(() {
        _bundle = b;
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

  Future<void> _toggle(String cat, bool muted) async {
    try {
      await context.read<Session>().api.muteReminderCategory(cat, muted: muted);
      await _load();
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final canMuteAnomaly = session.user?.role != UserRole.counselor;
    return Scaffold(
      appBar: AppBar(title: const Text('提醒中心'), automaticallyImplyLeading: Navigator.of(context).canPop()),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                children: [
                  if (_error != null) ErrorBanner(_error!, onRetry: _load),
                  const Text('可关闭某一类提醒。关闭后不再推送该类，但对应待办仍会保留，以免漏办。', style: TextStyle(height: 1.45)),
                  const SizedBox(height: 8),
                  for (final c in cats)
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(c.$2),
                      subtitle: Text(c.$1 == 'anomaly' && !canMuteAnomaly ? '辅导员不可关闭本班异常提醒' : (_bundle.mutedCategories.contains(c.$1) ? '已关闭此类推送' : '开启')),
                      value: !_bundle.mutedCategories.contains(c.$1),
                      onChanged: (c.$1 == 'anomaly' && !canMuteAnomaly)
                          ? null
                          : (v) => _toggle(c.$1, !v),
                    ),
                  const SizedBox(height: 8),
                  for (final c in cats) ...[
                    SectionTitle(c.$2),
                    ..._group(c.$1),
                  ],
                ],
              ),
            ),
    );
  }

  List<Widget> _group(String cat) {
    if (_bundle.mutedCategories.contains(cat)) {
      return [const Padding(padding: EdgeInsets.only(bottom: 12), child: Text('此类提醒已关闭。待办仍保留。'))];
    }
    final items = _bundle.items.where((e) => e.category == cat).toList();
    if (items.isEmpty) {
      return [const Padding(padding: EdgeInsets.only(bottom: 12), child: Text('暂时没有此类提醒。'))];
    }
    return [
      for (final item in items) ...[
        SoftCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, height: 1.35)),
              if (item.body != null) ...[
                const SizedBox(height: 6),
                Text(item.body!, style: const TextStyle(height: 1.45)),
              ],
              if (item.citations.isNotEmpty) ...[
                const SizedBox(height: 8),
                for (var i = 0; i < item.citations.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: CitationCard(
                      citation: item.citations[i],
                      index: i + 1,
                      onTap: () => AppNav.openCitation(context, item.citations[i]),
                    ),
                  ),
              ],
              if (item.action != null) ...[
                const SizedBox(height: 8),
                FilledButton(
                  onPressed: () => AppNav.openAction(context, type: item.action!.type, refId: item.action!.refId),
                  child: Text(item.action!.label),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 10),
      ],
    ];
  }
}
