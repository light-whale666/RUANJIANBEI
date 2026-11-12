import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class AidDraftScreen extends StatefulWidget {
  const AidDraftScreen({super.key, required this.programOrDraftId});

  final String programOrDraftId;

  @override
  State<AidDraftScreen> createState() => _AidDraftScreenState();
}

class _AidDraftScreenState extends State<AidDraftScreen> {
  AidDraft? _draft;
  AidMatch? _match;
  final _statement = TextEditingController();
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _statement.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = context.read<Session>().api;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      AidDraft? draft;
      try {
        draft = await api.getAidDraft(widget.programOrDraftId);
      } on ApiException catch (e) {
        if (e.status != 404 && e.code != 'not_found') rethrow;
      }
      draft ??= await api.createAidDraft(widget.programOrDraftId);
      List<AidMatch> matches = const [];
      try {
        matches = await api.aidMatches();
      } catch (_) {}
      if (!mounted) return;
      _statement.text = draft.statement ?? '';
      setState(() {
        _draft = draft;
        _match = matches.cast<AidMatch?>().firstWhere(
              (m) => m!.programId == draft!.programId || m.programId == widget.programOrDraftId,
              orElse: () => matches.isNotEmpty ? matches.first : null,
            );
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

  Future<void> _confirm() async {
    final draft = _draft!;
    final ok = await AppNav.openConfirm(
      context,
      payload: ConfirmPayload.fromAid(draft),
      onConfirm: () => context.read<Session>().api.confirmAidDraft(draft.id, fields: {'statement': _statement.text.trim()}),
    );
    if (ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('草稿已确认。系统没有自动向学校提交。')));
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final draft = _draft;
    return Scaffold(
      appBar: AppBar(title: const Text('奖助预审与草稿')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : draft == null
              ? Center(child: Text(_error ?? '无法生成草稿'))
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                  children: [
                    Text(draft.title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 6),
                    StatusChip(statusLabel(draft.status), tone: statusTone(draft.status)),
                    const SizedBox(height: 12),
                    if (_match?.reason != null)
                      SoftCard(
                        color: AppColors.tealSoft,
                        child: Text('匹配理由：${_match!.reason}', style: const TextStyle(height: 1.45)),
                      ),
                    const SizedBox(height: 8),
                    const Text('系统只做预审和草稿，不会自动提交。不够格的项目不会出现在这里。', style: TextStyle(color: AppColors.muted, height: 1.4)),
                    const SizedBox(height: 12),
                    FieldTable(fields: draft.fields),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _statement,
                      minLines: 3,
                      maxLines: 6,
                      decoration: const InputDecoration(labelText: '个人陈述（本次手填）'),
                    ),
                    if (draft.citations.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      const SectionTitle('条款依据'),
                      for (var i = 0; i < draft.citations.length; i++) ...[
                        CitationCard(citation: draft.citations[i], index: i + 1, onTap: () => AppNav.openCitation(context, draft.citations[i])),
                        const SizedBox(height: 8),
                      ],
                    ],
                    if (draft.status == 'confirmed_pending_submit') ...[
                      const SizedBox(height: 12),
                      const SoftCard(
                        color: AppColors.successSoft,
                        child: Text('草稿已确认，待按学校通道报送。若暂无校级对接，可把材料包交给学工窗口。系统没有代你提交。'),
                      ),
                    ] else ...[
                      const SizedBox(height: 16),
                      FilledButton(onPressed: _confirm, child: const Text('进入确认页')),
                    ],
                  ],
                ),
    );
  }
}
