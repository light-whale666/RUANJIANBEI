import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class ApprovalDetailScreen extends StatefulWidget {
  const ApprovalDetailScreen({super.key, required this.approvalId, this.preview});

  final String approvalId;
  final ApprovalItem? preview;

  @override
  State<ApprovalDetailScreen> createState() => _ApprovalDetailScreenState();
}

class _ApprovalDetailScreenState extends State<ApprovalDetailScreen> {
  late ApprovalItem? _item = widget.preview;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (_item == null) _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final list = await context.read<Session>().api.approvals();
      if (!mounted) return;
      setState(() {
        _item = list.where((e) => e.id == widget.approvalId).firstOrNull;
        _error = _item == null ? '未找到该审批。' : null;
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

  Future<void> _decide(String decision) async {
    final commentCtrl = TextEditingController();
    if (decision == 'reject' || decision == 'transfer') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(decision == 'reject' ? '退回原因（必填）' : '转交说明'),
          content: TextField(controller: commentCtrl, minLines: 2, maxLines: 4, decoration: const InputDecoration(hintText: '请填写原因')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('确定')),
          ],
        ),
      );
      if (ok != true) return;
      if (decision == 'reject' && commentCtrl.text.trim().isEmpty) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('驳回必须填写原因。')));
        return;
      }
    }
    try {
      await context.read<Session>().api.decideApproval(
            widget.approvalId,
            decision: decision,
            comment: commentCtrl.text.trim().isEmpty ? null : commentCtrl.text.trim(),
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(decision == 'approve' ? '已批准。系统没有代替你审批之外的操作。' : '已处理。')));
      Navigator.pop(context);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = _item;
    return Scaffold(
      appBar: AppBar(title: const Text('审批详情')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : item == null
              ? Center(child: Text(_error ?? '未找到'))
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                  children: [
                    Row(
                      children: [
                        Expanded(child: Text('${item.applicantName} 的${item.title}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700))),
                        StatusChip(statusLabel(item.status), tone: statusTone(item.status)),
                      ],
                    ),
                    if (item.summary != null) ...[
                      const SizedBox(height: 8),
                      Text(item.summary!, style: const TextStyle(height: 1.45)),
                    ],
                    if (item.leave?.durationText != null) ...[
                      const SizedBox(height: 8),
                      Text('时长：${item.leave!.durationText}'),
                    ],
                    if (item.validation != null) ...[
                      const SizedBox(height: 12),
                      SoftCard(
                        color: item.validation!.ok ? AppColors.successSoft : AppColors.dangerSoft,
                        child: Text(item.validation!.message ?? (item.validation!.ok ? '校验通过' : '校验未通过')),
                      ),
                    ],
                    const SizedBox(height: 12),
                    FieldTable(fields: item.fields.isNotEmpty ? item.fields : (item.leave?.fields ?? const [])),
                    if (item.attachments.isNotEmpty || (item.leave?.attachments.isNotEmpty ?? false)) ...[
                      const SizedBox(height: 10),
                      SoftCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('附件', style: TextStyle(fontWeight: FontWeight.w600)),
                            for (final a in [...item.attachments, ...?item.leave?.attachments]) Text('· ${a.filename}'),
                          ],
                        ),
                      ),
                    ],
                    if (item.citations.isNotEmpty || (item.leave?.citations.isNotEmpty ?? false)) ...[
                      const SizedBox(height: 12),
                      const SectionTitle('依据'),
                      for (final c in [...item.citations, ...?item.leave?.citations]) ...[
                        CitationCard(citation: c, onTap: () => AppNav.openCitation(context, c)),
                        const SizedBox(height: 8),
                      ],
                    ],
                    if (item.status == 'pending') ...[
                      const SizedBox(height: 16),
                      FilledButton(onPressed: () => _decide('approve'), child: const Text('批准')),
                      const SizedBox(height: 8),
                      OutlinedButton(onPressed: () => _decide('reject'), child: const Text('退回（必填原因）')),
                      const SizedBox(height: 8),
                      TextButton(onPressed: () => _decide('transfer'), child: const Text('转交')),
                    ],
                  ],
                ),
    );
  }
}
