import 'package:flutter/material.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class ConfirmScreen extends StatefulWidget {
  const ConfirmScreen({super.key, required this.payload, required this.onConfirm});

  final ConfirmPayload payload;
  final Future<void> Function() onConfirm;

  @override
  State<ConfirmScreen> createState() => _ConfirmScreenState();
}

class _ConfirmScreenState extends State<ConfirmScreen> {
  bool _busy = false;
  bool _acked = false;

  Future<void> _submit() async {
    if (!_acked) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('请先勾选：我已核对以上信息，确认提交。')));
      return;
    }
    setState(() => _busy = true);
    try {
      await widget.onConfirm();
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.payload;
    return Scaffold(
      appBar: AppBar(title: Text(p.title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          if (p.headline != null && p.headline!.isNotEmpty) ...[
            Text(p.headline!, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
          ],
          for (final w in p.warnings) ...[
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(color: AppColors.warningSoft, borderRadius: BorderRadius.circular(12)),
              child: Text(w, style: const TextStyle(height: 1.4, color: AppColors.warning)),
            ),
          ],
          FieldTable(title: '档案预填', fields: p.prefills),
          if (p.manuals.isNotEmpty) ...[
            const SizedBox(height: 10),
            FieldTable(title: '本次手填 / 识别', fields: p.manuals),
          ],
          if (p.attachments.isNotEmpty) ...[
            const SizedBox(height: 10),
            SoftCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('附件', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  for (final a in p.attachments)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Text('· ${a.filename}  ${a.validityLabel}', style: const TextStyle(height: 1.4)),
                    ),
                ],
              ),
            ),
          ],
          if (p.approvers.isNotEmpty) ...[
            const SizedBox(height: 10),
            SoftCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('将送给这些审批人', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  for (final a in p.approvers)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Text('第${a.order}级  ${a.name}（${a.role}）', style: const TextStyle(height: 1.4)),
                    ),
                ],
              ),
            ),
          ],
          if (p.citations.isNotEmpty) ...[
            const SizedBox(height: 12),
            const SectionTitle('所依据的条款'),
            for (var i = 0; i < p.citations.length; i++) ...[
              CitationCard(
                citation: p.citations[i],
                index: i + 1,
                onTap: () => AppNav.openCitation(context, p.citations[i]),
              ),
              const SizedBox(height: 8),
            ],
          ],
          if (p.legalNote != null) ...[
            const SizedBox(height: 8),
            Text(p.legalNote!, style: const TextStyle(color: AppColors.muted, height: 1.45, fontSize: 13)),
          ],
          const SizedBox(height: 12),
          CheckboxListTile(
            value: _acked,
            onChanged: (v) => setState(() => _acked = v ?? false),
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            title: const Text('我已核对以上信息，确认提交。系统不会代替我确认或代替老师审批。'),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : Text(p.submitLabel),
          ),
        ],
      ),
    );
  }
}
