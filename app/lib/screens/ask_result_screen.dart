import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class AskResultScreen extends StatefulWidget {
  const AskResultScreen({super.key, required this.result, required this.question});

  final AskResult result;
  final String question;

  @override
  State<AskResultScreen> createState() => _AskResultScreenState();
}

class _AskResultScreenState extends State<AskResultScreen> {
  late AskResult _result;
  final Map<String, TextEditingController> _slots = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _result = widget.result;
    for (final s in _result.slotsNeeded) {
      _slots[s.field] = TextEditingController();
    }
  }

  @override
  void dispose() {
    for (final c in _slots.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _fillSlots() async {
    final values = {for (final e in _slots.entries) e.key: e.value.text.trim()};
    if (values.values.any((v) => v.isEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('请先补全这些信息，只会再问这一轮。')));
      return;
    }
    setState(() => _busy = true);
    final session = context.read<Session>();
    try {
      final next = await session.guard(() => session.api.ask(
            text: widget.question,
            slots: values,
          ));
      if (!mounted) return;
      setState(() => _result = next);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _human() async {
    final label = _result.humanEntry?.label ?? '转给辅导员';
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(label),
        content: const Text('系统不会代替辅导员回答无权限或库中没有的规定。请联系辅导员或学校办事窗口。演示环境不会自动发送站内信。'),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('知道了'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final r = _result;
    return Scaffold(
      appBar: AppBar(title: const Text('答复')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          Text(widget.question, style: const TextStyle(color: AppColors.muted, height: 1.4)),
          const SizedBox(height: 16),
          const SectionTitle('结论'),
          SoftCard(
            child: r.permissionDenied
                ? const Text(
                    '该规定需辅导员查看。系统不会展示无权限正文，也不会以打码方式泄露条款。',
                    style: TextStyle(fontSize: 16, height: 1.55, fontWeight: FontWeight.w600),
                  )
                : ConclusionView(text: r.conclusion, citations: r.citations),
          ),
          if (r.conflicts.isNotEmpty) ...[
            const SizedBox(height: 12),
            ConflictBanner(conflicts: r.conflicts),
          ],
          if (!r.permissionDenied) ...[
            const SizedBox(height: 16),
            const SectionTitle('依据'),
            if (r.citations.isEmpty)
              const SoftCard(
                child: Text(
                  '知识库中没有找到相关规定，因此没有依据卡片。系统不会编造条款。',
                  style: TextStyle(height: 1.5),
                ),
              )
            else
              ...[
                for (var i = 0; i < r.citations.length; i++) ...[
                  CitationCard(
                    citation: r.citations[i],
                    index: i + 1,
                    onTap: () => AppNav.openCitation(context, r.citations[i]),
                  ),
                  const SizedBox(height: 8),
                ],
              ],
          ],
          if (r.slotsNeeded.isNotEmpty) ...[
            const SizedBox(height: 16),
            const SectionTitle('请补全这些信息'),
            SoftCard(
              child: Column(
                children: [
                  for (final s in r.slotsNeeded) ...[
                    TextField(
                      controller: _slots[s.field],
                      decoration: InputDecoration(labelText: s.question),
                    ),
                    const SizedBox(height: 10),
                  ],
                  FilledButton(onPressed: _busy ? null : _fillSlots, child: const Text('补全后继续')),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
          const SectionTitle('去办理 / 生成草稿'),
          if (r.action != null)
            FilledButton(
              onPressed: () => AppNav.openAction(
                context,
                type: r.action!.type,
                refId: r.action!.refId,
              ),
              child: Text(r.action!.label),
            )
          else if (r.humanEntry != null)
            FilledButton(onPressed: _human, child: Text(r.humanEntry!.label))
          else
            const SoftCard(child: Text('这是查阅类答复，没有对应的办理事项。')),
          if (r.action != null && r.humanEntry != null) ...[
            const SizedBox(height: 8),
            OutlinedButton(onPressed: _human, child: Text(r.humanEntry!.label)),
          ],
          if (r.permissionDenied && r.humanEntry != null) ...[
            const SizedBox(height: 8),
            // already has button above when action is null
          ],
        ],
      ),
    );
  }
}

class ConclusionView extends StatelessWidget {
  const ConclusionView({super.key, required this.text, required this.citations});

  final String text;
  final List<Citation> citations;

  @override
  Widget build(BuildContext context) {
    final spans = <InlineSpan>[];
    final reg = RegExp(r'(\^?\[(\d+)\]|［(\d+)］)');
    var last = 0;
    for (final m in reg.allMatches(text)) {
      if (m.start > last) {
        spans.add(TextSpan(text: text.substring(last, m.start)));
      }
      final n = int.tryParse(m.group(2) ?? m.group(3) ?? '') ?? 0;
      spans.add(WidgetSpan(
        alignment: PlaceholderAlignment.top,
        child: GestureDetector(
          onTap: () {
            if (n >= 1 && n <= citations.length) {
              AppNav.openCitation(context, citations[n - 1]);
            }
          },
          child: Padding(
            padding: const EdgeInsets.only(left: 1, right: 1, bottom: 6),
            child: Text('$n', style: const TextStyle(color: AppColors.teal, fontSize: 11, fontWeight: FontWeight.w700, height: 1)),
          ),
        ),
      ));
      last = m.end;
    }
    if (last < text.length) spans.add(TextSpan(text: text.substring(last)));
    if (spans.isEmpty) spans.add(TextSpan(text: text));
    return Text.rich(
      TextSpan(style: const TextStyle(fontSize: 16, height: 1.55, color: AppColors.ink, fontWeight: FontWeight.w600), children: spans),
    );
  }
}
