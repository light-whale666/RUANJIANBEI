import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import 'progress_screen.dart';

class PublishTaskScreen extends StatefulWidget {
  const PublishTaskScreen({super.key});

  @override
  State<PublishTaskScreen> createState() => _PublishTaskScreenState();
}

class _PublishTaskScreenState extends State<PublishTaskScreen> {
  String _type = 'homework';
  final _title = TextEditingController();
  final _body = TextEditingController();
  final _audience = TextEditingController();
  final _location = TextEditingController();
  DateTime _due = DateTime(2026, 11, 18, 18);
  String _submitMode = 'file';
  bool _needReview = false;
  bool _busy = false;

  @override
  void dispose() {
    _title.dispose();
    _body.dispose();
    _audience.dispose();
    _location.dispose();
    super.dispose();
  }

  Future<void> _pickDue() async {
    final d = await showDatePicker(context: context, initialDate: _due, firstDate: DateTime(2025), lastDate: DateTime(2028));
    if (d == null || !mounted) return;
    final t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_due));
    setState(() => _due = DateTime(d.year, d.month, d.day, t?.hour ?? 18, t?.minute ?? 0));
  }

  Future<void> _publish() async {
    if (_title.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('请填写标题')));
      return;
    }
    setState(() => _busy = true);
    try {
      final task = await context.read<Session>().api.createTask(
            type: _type,
            title: _title.text.trim(),
            body: _body.text.trim(),
            dueAt: _due,
            audience: _audience.text.trim().isEmpty ? null : _audience.text.trim(),
            extra: {
              'submit_mode': _submitMode,
              'location': _location.text.trim(),
              'need_review': _needReview,
            },
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已发布，将进入对应学生的待办。')));
      await AppNav.push(context, ProgressScreen(taskId: task.id));
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('发布'), automaticallyImplyLeading: Navigator.of(context).canPop()),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          const Text('可发布作业、志愿者招募或报到/班级任务。发布后进入对应学生的同一条待办流。', style: TextStyle(color: AppColors.muted, height: 1.45)),
          const SizedBox(height: 12),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'homework', label: Text('作业')),
              ButtonSegment(value: 'volunteer', label: Text('招募')),
              ButtonSegment(value: 'registration', label: Text('报到/班级')),
            ],
            selected: {_type},
            onSelectionChanged: (s) => setState(() => _type = s.first),
          ),
          const SizedBox(height: 12),
          TextField(controller: _title, decoration: const InputDecoration(labelText: '标题')),
          const SizedBox(height: 8),
          TextField(controller: _body, minLines: 3, maxLines: 6, decoration: const InputDecoration(labelText: '说明')),
          const SizedBox(height: 8),
          TextField(controller: _audience, decoration: const InputDecoration(labelText: '对象范围（课程或班级）', hintText: '例如：26软件1班')),
          const SizedBox(height: 8),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('截止时间'),
            subtitle: Text(dateFmt.format(_due)),
            onTap: _pickDue,
            trailing: const Icon(Icons.schedule),
          ),
          if (_type == 'volunteer')
            TextField(controller: _location, decoration: const InputDecoration(labelText: '地点')),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: _submitMode,
            decoration: const InputDecoration(labelText: '提交方式'),
            items: const [
              DropdownMenuItem(value: 'none', child: Text('无需提交')),
              DropdownMenuItem(value: 'confirm', child: Text('仅确认已完成')),
              DropdownMenuItem(value: 'file', child: Text('上传文件')),
              DropdownMenuItem(value: 'signup', child: Text('报名表')),
            ],
            onChanged: (v) => setState(() => _submitMode = v ?? 'file'),
          ),
          if (_type == 'volunteer')
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('报名需要审核'),
              value: _needReview,
              onChanged: (v) => setState(() => _needReview = v),
            ),
          const SizedBox(height: 16),
          FilledButton(onPressed: _busy ? null : _publish, child: const Text('发布')),
        ],
      ),
    );
  }
}
