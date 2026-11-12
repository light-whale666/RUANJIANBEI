import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class ProgressScreen extends StatefulWidget {
  const ProgressScreen({super.key, required this.taskId});

  final String taskId;

  @override
  State<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends State<ProgressScreen> {
  bool _loading = true;
  String? _error;
  dynamic _data;

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
      final p = await context.read<Session>().api.taskProgress(widget.taskId);
      if (!mounted) return;
      setState(() {
        _data = p;
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

  @override
  Widget build(BuildContext context) {
    final p = _data;
    return Scaffold(
      appBar: AppBar(title: Text(p?.title ?? '进度名单')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : p == null
              ? Center(child: Text(_error ?? '暂无数据'))
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                  children: [
                    SoftCard(
                      color: AppColors.tealSoft,
                      child: Text('完成 ${p.completed} / ${p.total}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                    ),
                    const SizedBox(height: 12),
                    if (p.rows.isEmpty)
                      const EmptyView(title: '还没有名单', subtitle: '发布后，对象学生的完成情况会显示在这里。')
                    else
                      for (final row in p.rows) ...[
                        SoftCard(
                          color: row.overdue ? AppColors.dangerSoft : AppColors.card,
                          child: Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(row.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                                    Text(row.className ?? '', style: const TextStyle(color: AppColors.muted, fontSize: 12.5)),
                                  ],
                                ),
                              ),
                              StatusChip(
                                row.overdue ? '未完成（标红）' : statusLabel(row.status),
                                tone: row.overdue ? 'bad' : statusTone(row.status),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                      ],
                  ],
                ),
    );
  }
}
