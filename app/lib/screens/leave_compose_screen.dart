import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class LeaveComposeScreen extends StatefulWidget {
  const LeaveComposeScreen({
    super.key,
    this.presetReason,
    this.asCertificate = false,
    this.reuseAttachmentIds = const [],
  });

  final String? presetReason;
  final bool asCertificate;
  final List<String> reuseAttachmentIds;

  @override
  State<LeaveComposeScreen> createState() => _LeaveComposeScreenState();
}

class _LeaveComposeScreenState extends State<LeaveComposeScreen> {
  final _reason = TextEditingController();
  final _dest = TextEditingController();
  final _picker = ImagePicker();
  DateTime _start = DateTime(2026, 11, 11, 8);
  DateTime _end = DateTime(2026, 11, 11, 12);
  final List<AttachmentInfo> _uploaded = [];
  List<AttachmentInfo> _reusable = [];
  final Set<String> _chosen = {};
  bool _busy = false;
  List<MissingItem> _missing = [];

  @override
  void initState() {
    super.initState();
    _reason.text = widget.presetReason ?? '';
    _chosen.addAll(widget.reuseAttachmentIds);
    _loadReusable();
  }

  @override
  void dispose() {
    _reason.dispose();
    _dest.dispose();
    super.dispose();
  }

  Future<void> _loadReusable() async {
    try {
      final files = await context.read<Session>().api.myAttachments();
      if (!mounted) return;
      setState(() => _reusable = files);
    } catch (_) {}
  }

  Future<void> _pickDate({required bool start}) async {
    final seed = start ? _start : _end;
    final d = await showDatePicker(
      context: context,
      initialDate: seed,
      firstDate: DateTime(2025),
      lastDate: DateTime(2028),
    );
    if (d == null || !mounted) return;
    final t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(seed));
    final next = DateTime(d.year, d.month, d.day, t?.hour ?? seed.hour, t?.minute ?? seed.minute);
    setState(() {
      if (start) {
        _start = next;
        if (_end.isBefore(_start)) _end = _start.add(const Duration(hours: 4));
      } else {
        _end = next;
      }
    });
  }

  Future<void> _addPhoto() async {
    final file = await _picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (file == null) return;
    setState(() => _busy = true);
    try {
      final att = await context.read<Session>().api.uploadAttachment(file.path, filename: file.name, kind: 'proof');
      setState(() {
        _uploaded.add(att);
        _chosen.add(att.id);
      });
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _missing = [];
    });
    final session = context.read<Session>();
    final ids = _chosen.toList();
    try {
      final leave = await session.guard(() => session.api.createLeave(
            text: _reason.text.trim(),
            attachmentIds: ids,
            fields: {
              'reason': _reason.text.trim(),
              'destination': _dest.text.trim(),
              'start_at': _start.toIso8601String(),
              'end_at': _end.toIso8601String(),
            },
          ));
      if (!mounted) return;
      if (!leave.validation.ok) {
        setState(() => _missing = leave.validation.missing);
        return;
      }
      final ok = await AppNav.openConfirm(
        context,
        payload: ConfirmPayload.fromLeave(leave),
        onConfirm: () => session.api.confirmLeave(leave.id),
      );
      if (ok && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已提交，等待审批。系统没有代替你确认。')));
        Navigator.pop(context, true);
      }
    } on ApiException catch (e) {
      if (e.isValidationBlocked) {
        setState(() {
          _missing = [
            for (final m in e.missingMessages) MissingItem(field: 'item', message: m),
          ];
        });
        final leaveId = e.details?['leave_id'] as String?;
        if (leaveId != null && mounted) {
          // keep user here to supplement
        }
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cert = widget.asCertificate;
    return Scaffold(
      appBar: AppBar(title: Text(cert ? '补证 / 开具证明' : '请假')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          Text(cert ? '档案将自动预填。请补充用途、份数或原因，提交前必须确认。' : '一句话说明原因即可，也可以附上假条或病例照片。档案会自动预填，提交前必须经过确认页。', style: const TextStyle(height: 1.45, color: AppColors.muted)),
          const SizedBox(height: 12),
          TextField(
            controller: _reason,
            minLines: 2,
            maxLines: 4,
            decoration: InputDecoration(labelText: cert ? '用途与原因' : '请假原因或一句话说明', hintText: cert ? '例如：实习开具在读证明' : '例如：周三下午去医院复查'),
          ),
          const SizedBox(height: 8),
          if (!cert) TextField(controller: _dest, decoration: const InputDecoration(labelText: '去向')),
          const SizedBox(height: 8),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('开始时间'),
            subtitle: Text(dateFmt.format(_start)),
            onTap: () => _pickDate(start: true),
            trailing: const Icon(Icons.schedule),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('结束时间'),
            subtitle: Text(dateFmt.format(_end)),
            onTap: () => _pickDate(start: false),
            trailing: const Icon(Icons.schedule),
          ),
          const SectionTitle('材料'),
          Wrap(
            spacing: 8,
            children: [
              OutlinedButton.icon(onPressed: _addPhoto, icon: const Icon(Icons.photo_outlined), label: const Text('添加照片')),
            ],
          ),
          const SizedBox(height: 8),
          for (final a in [..._uploaded, ..._reusable])
            CheckboxListTile(
              value: _chosen.contains(a.id),
              onChanged: a.expired
                  ? null
                  : (v) => setState(() {
                        if (v == true) {
                          _chosen.add(a.id);
                        } else {
                          _chosen.remove(a.id);
                        }
                      }),
              title: Text(a.filename),
              subtitle: Text(a.expired ? '已过期，不可选用' : a.validityLabel),
              controlAffinity: ListTileControlAffinity.leading,
              contentPadding: EdgeInsets.zero,
            ),
          if (_missing.isNotEmpty) ...[
            const SizedBox(height: 8),
            SoftCard(
              color: AppColors.dangerSoft,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('材料不全，已当场拦住，尚未生成可提交单据。', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.danger)),
                  const SizedBox(height: 8),
                  for (final m in _missing) Text('· ${m.message}', style: const TextStyle(height: 1.4)),
                  const SizedBox(height: 8),
                  const Text('请拍照补充或改时间后重试。'),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Text('校验并进入确认页'),
          ),
        ],
      ),
    );
  }
}
