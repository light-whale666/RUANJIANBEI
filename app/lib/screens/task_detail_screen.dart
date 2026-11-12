import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import 'progress_screen.dart';

class TaskDetailScreen extends StatefulWidget {
  const TaskDetailScreen({super.key, required this.taskId});

  final String taskId;

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  TaskItem? _task;
  bool _loading = true;
  String? _error;
  final _note = TextEditingController();
  final _slot = TextEditingController();
  final List<String> _atts = [];
  final _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _note.dispose();
    _slot.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final task = await context.read<Session>().api.getTask(widget.taskId);
      if (!mounted) return;
      final preset = task.prefills.where((f) => f.field == 'slot').firstOrNull;
      if (preset != null) _slot.text = preset.value;
      setState(() {
        _task = task;
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

  Future<void> _addFile() async {
    final file = await _picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (file == null) return;
    try {
      final att = await context.read<Session>().api.uploadAttachment(file.path, filename: file.name);
      setState(() => _atts.add(att.id));
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _submit() async {
    final task = _task!;
    if (task.signupValidation != null && !task.signupValidation!.ok) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(task.signupValidation!.message ?? '不符合条件，不能提交。')));
      return;
    }
    final manuals = [
      ...task.prefills.where((f) => f.source != 'profile' && f.source != 'unauthorized'),
      if (_slot.text.trim().isNotEmpty)
        FieldSource(field: 'slot', label: '可参加时段', value: _slot.text.trim(), source: 'manual'),
      if (_note.text.trim().isNotEmpty)
        FieldSource(field: 'note', label: '说明', value: _note.text.trim(), source: 'manual'),
    ];
    final payload = ConfirmPayload(
      title: task.type == 'volunteer' ? '确认报名信息' : '确认提交',
      headline: task.title,
      prefills: task.prefills.where((f) => f.source == 'profile' || f.source == 'unauthorized').toList(),
      manuals: manuals,
      citations: task.citations,
      legalNote: '请核对后再确认。系统不会代替你提交。',
      submitLabel: task.type == 'volunteer' ? '确认报名' : '确认提交',
    );
    final ok = await AppNav.openConfirm(
      context,
      payload: payload,
      onConfirm: () => context.read<Session>().api.submitTask(
            task.id,
            note: _note.text.trim().isEmpty ? null : _note.text.trim(),
            attachmentIds: _atts,
            fields: {if (_slot.text.trim().isNotEmpty) 'slot': _slot.text.trim()},
          ),
    );
    if (ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已提交。')));
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final task = _task;
    return Scaffold(
      appBar: AppBar(title: Text(task?.type == 'volunteer' ? '志愿者招募' : (task?.type == 'registration' ? '报到任务' : '任务'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : task == null
              ? Center(child: Text(_error ?? '未找到任务'))
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                  children: [
                    Text(task.title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                    if (task.dueAt != null) ...[
                      const SizedBox(height: 6),
                      Text(formatDue(task.dueAt), style: const TextStyle(color: AppColors.muted)),
                    ],
                    if (task.location != null || task.timeText != null) ...[
                      const SizedBox(height: 6),
                      Text([task.timeText, task.location].whereType<String>().join(' · ')),
                    ],
                    if (task.body != null) ...[
                      const SizedBox(height: 12),
                      Text(task.body!, style: const TextStyle(height: 1.5)),
                    ],
                    if (task.capacity != null) ...[
                      const SizedBox(height: 8),
                      Text('名额 ${task.signedUp ?? 0} / ${task.capacity}'),
                    ],
                    if (task.prefills.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      FieldTable(title: '将预填的信息', fields: task.prefills.where((f) => f.value.isNotEmpty || f.source == 'unauthorized').toList()),
                    ],
                    if (task.type == 'volunteer') ...[
                      const SizedBox(height: 12),
                      TextField(controller: _slot, decoration: const InputDecoration(labelText: '可参加时段（本次手填）')),
                    ],
                    if (task.submitMode == 'file') ...[
                      const SizedBox(height: 12),
                      OutlinedButton.icon(onPressed: _addFile, icon: const Icon(Icons.attach_file), label: Text(_atts.isEmpty ? '上传提交物' : '已选 ${_atts.length} 个文件')),
                    ],
                    if (task.submitMode != 'confirm' && task.type != 'volunteer') ...[
                      const SizedBox(height: 8),
                      TextField(controller: _note, decoration: const InputDecoration(labelText: '说明（可选）')),
                    ],
                    if (task.signupValidation != null && !task.signupValidation!.ok) ...[
                      const SizedBox(height: 12),
                      SoftCard(
                        color: AppColors.dangerSoft,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('不符合条件，不能提交。', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.danger)),
                            const SizedBox(height: 6),
                            for (final m in task.signupValidation!.missing) Text('· ${m.message}', style: const TextStyle(height: 1.4)),
                          ],
                        ),
                      ),
                    ],
                    if (task.citations.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      const SectionTitle('依据'),
                      for (var i = 0; i < task.citations.length; i++) ...[
                        CitationCard(citation: task.citations[i], index: i + 1, onTap: () => AppNav.openCitation(context, task.citations[i])),
                        const SizedBox(height: 8),
                      ],
                    ],
                    const SizedBox(height: 16),
                    if (task.status == 'submitted')
                      const SoftCard(color: AppColors.successSoft, child: Text('你已完成此项。'))
                    else if (task.signupValidation != null && !task.signupValidation!.ok)
                      const FilledButton(onPressed: null, child: Text('不能提交'))
                    else
                      FilledButton(
                        onPressed: _submit,
                        child: Text(task.type == 'volunteer' ? '核验并报名' : '进入确认页'),
                      ),
                    if (context.watch<Session>().isStaff) ...[
                      const SizedBox(height: 8),
                      OutlinedButton(
                        onPressed: () => AppNav.push(context, ProgressScreen(taskId: task.id)),
                        child: const Text('查看进度名单'),
                      ),
                    ],
                  ],
                ),
    );
  }
}
