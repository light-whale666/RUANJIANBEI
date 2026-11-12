import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../screens/leave_compose_screen.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../widgets/ui.dart';

class ApplicationsScreen extends StatefulWidget {
  const ApplicationsScreen({super.key});

  @override
  State<ApplicationsScreen> createState() => _ApplicationsScreenState();
}

class _ApplicationsScreenState extends State<ApplicationsScreen> {
  List<ApplicationItem> _apps = [];
  List<AttachmentInfo> _files = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = context.read<Session>().api;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final apps = await api.myApplications();
      final files = await api.myAttachments();
      if (!mounted) return;
      setState(() {
        _apps = apps;
        _files = files;
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
    return Scaffold(
      appBar: AppBar(title: const Text('我的申请与材料'), automaticallyImplyLeading: Navigator.of(context).canPop()),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                children: [
                  if (_error != null) ErrorBanner(_error!, onRetry: _load),
                  const SectionTitle('历史单据'),
                  if (_apps.isEmpty)
                    const EmptyView(title: '还没有申请记录', subtitle: '请假、证明和奖助草稿会显示在这里。')
                  else
                    for (final a in _apps) ...[
                      SoftCard(
                        onTap: () => AppNav.openAction(context, type: a.kind, refId: a.refId ?? a.id),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(a.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                                  const SizedBox(height: 4),
                                  Text(_kindLabel(a.kind), style: const TextStyle(color: Color(0xFF5C6764))),
                                ],
                              ),
                            ),
                            StatusChip(statusLabel(a.status), tone: statusTone(a.status)),
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                  const SizedBox(height: 12),
                  const SectionTitle('可复用材料'),
                  const Text('有效期内可在请假等办理中一键带入，仍须走确认页。过期材料不可选。', style: TextStyle(height: 1.4)),
                  const SizedBox(height: 8),
                  if (_files.isEmpty)
                    const EmptyView(title: '还没有已上传的材料', icon: Icons.attachment)
                  else
                    for (final f in _files) ...[
                      SoftCard(
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(f.filename, style: const TextStyle(fontWeight: FontWeight.w600)),
                                  Text(f.validityLabel, style: const TextStyle(color: Color(0xFF5C6764), fontSize: 12.5)),
                                ],
                              ),
                            ),
                            if (!f.expired)
                              TextButton(
                                onPressed: () => AppNav.push(
                                  context,
                                  LeaveComposeScreen(reuseAttachmentIds: [f.id]),
                                ),
                                child: const Text('复用'),
                              )
                            else
                              const StatusChip('已过期', tone: 'bad'),
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                ],
              ),
            ),
    );
  }

  String _kindLabel(String kind) {
    switch (kind) {
      case 'leave':
        return '请假';
      case 'aid':
        return '奖助草稿';
      case 'certificate':
        return '证明 / 补证';
      case 'volunteer':
        return '志愿者报名';
      default:
        return kind;
    }
  }
}
