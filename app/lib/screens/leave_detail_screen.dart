import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class LeaveDetailScreen extends StatefulWidget {
  const LeaveDetailScreen({super.key, required this.leaveId, this.startInReturn = false});

  final String leaveId;
  final bool startInReturn;

  @override
  State<LeaveDetailScreen> createState() => _LeaveDetailScreenState();
}

class _LeaveDetailScreenState extends State<LeaveDetailScreen> {
  LeaveRecord? _leave;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load(thenReturn: widget.startInReturn);
  }

  Future<void> _load({bool thenReturn = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final leave = await context.read<Session>().api.getLeave(widget.leaveId);
      if (!mounted) return;
      setState(() {
        _leave = leave;
        _loading = false;
      });
      if (thenReturn) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _returnLeave());
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    }
  }

  Future<void> _confirm() async {
    final leave = _leave!;
    final ok = await AppNav.openConfirm(
      context,
      payload: ConfirmPayload.fromLeave(leave),
      onConfirm: () => context.read<Session>().api.confirmLeave(leave.id),
    );
    if (ok) _load();
  }

  Future<void> _withdraw() async {
    try {
      await context.read<Session>().api.withdrawLeave(widget.leaveId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已撤回。')));
        _load();
      }
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _returnLeave() async {
    final leave = _leave;
    if (leave == null) return;
    if (leave.status != 'pending_return' && leave.status != 'approved') {
      return;
    }
    final payload = ConfirmPayload(
      title: '确认销假',
      headline: '返校时间默认预填为假期结束日，请核对。',
      prefills: leave.fields.where((f) => f.source == 'profile').toList(),
      manuals: [
        ...leave.fields.where((f) => f.source != 'profile'),
        FieldSource(
          field: 'returned_at',
          label: '返校时间',
          value: leave.endAt != null ? dateFmt.format(leave.endAt!) : '现在',
          source: 'manual',
        ),
      ],
      citations: leave.citations,
      legalNote: '销假同样需要你亲自确认。系统不会代替你提交。',
      submitLabel: '确认销假',
    );
    final ok = await AppNav.openConfirm(
      context,
      payload: payload,
      onConfirm: () => context.read<Session>().api.returnLeave(leave.id, returnedAt: leave.endAt),
    );
    if (ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('销假已确认。')));
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final leave = _leave;
    return Scaffold(
      appBar: AppBar(title: const Text('请假详情')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : leave == null
              ? Center(child: Text(_error ?? '未找到'))
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                  children: [
                    Row(
                      children: [
                        Expanded(child: Text(leave.durationText ?? '请假', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700))),
                        StatusChip(statusLabel(leave.status), tone: statusTone(leave.status)),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (!leave.validation.ok)
                      SoftCard(
                        color: AppColors.dangerSoft,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('校验未通过，不能进入确认页。', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.danger)),
                            for (final m in leave.validation.missing) Text('· ${m.message}'),
                          ],
                        ),
                      ),
                    if (leave.conflictNote != null) ...[
                      const SizedBox(height: 8),
                      SoftCard(color: AppColors.warningSoft, child: Text(leave.conflictNote!)),
                    ],
                    const SizedBox(height: 10),
                    FieldTable(fields: leave.fields),
                    if (leave.attachments.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      SoftCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('附件', style: TextStyle(fontWeight: FontWeight.w600)),
                            for (final a in leave.attachments) Text('· ${a.filename}  ${a.validityLabel}'),
                          ],
                        ),
                      ),
                    ],
                    if (leave.approvers.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      SoftCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('审批链', style: TextStyle(fontWeight: FontWeight.w600)),
                            for (final a in leave.approvers)
                              Text('第${a.order}级  ${a.name}（${a.role}）${a.status != null ? ' · ${statusLabel(a.status)}' : ''}'),
                          ],
                        ),
                      ),
                    ],
                    if (leave.citations.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      const SectionTitle('依据'),
                      for (var i = 0; i < leave.citations.length; i++) ...[
                        CitationCard(citation: leave.citations[i], index: i + 1, onTap: () => AppNav.openCitation(context, leave.citations[i])),
                        const SizedBox(height: 8),
                      ],
                    ],
                    const SizedBox(height: 16),
                    if (leave.canConfirm)
                      FilledButton(onPressed: _confirm, child: const Text('进入确认页')),
                    if (leave.status == 'pending_return' || leave.status == 'approved') ...[
                      const SizedBox(height: 8),
                      FilledButton(onPressed: _returnLeave, child: const Text('去销假')),
                    ],
                    if (leave.status == 'pending_confirm' || leave.status == 'submitted' || leave.status == 'approving') ...[
                      const SizedBox(height: 8),
                      OutlinedButton(onPressed: _withdraw, child: const Text('撤回申请')),
                    ],
                  ],
                ),
    );
  }
}
