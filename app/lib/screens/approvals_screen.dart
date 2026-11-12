import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../widgets/ui.dart';
import 'approval_detail_screen.dart';

class ApprovalsScreen extends StatefulWidget {
  const ApprovalsScreen({super.key});

  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  List _items = [];
  bool _loading = true;
  String? _error;

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
      final items = await context.read<Session>().api.approvals(type: 'leave');
      if (!mounted) return;
      setState(() {
        _items = items;
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
      appBar: AppBar(title: const Text('审批箱'), automaticallyImplyLeading: Navigator.of(context).canPop()),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                children: [
                  if (_error != null) ErrorBanner(_error!, onRetry: _load),
                  const Text('查看申请摘要、时长、依据、附件和校验结果。批准、退回（必填原因）或在规则允许时转交。系统不会代替老师审批。', style: TextStyle(height: 1.45)),
                  const SizedBox(height: 12),
                  if (_items.isEmpty)
                    const EmptyView(title: '审批箱是空的', icon: Icons.fact_check_outlined)
                  else
                    for (final item in _items) ...[
                      SoftCard(
                        onTap: () async {
                          await AppNav.push(context, ApprovalDetailScreen(approvalId: item.id, preview: item));
                          _load();
                        },
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('${item.applicantName}  ·  ${item.title}', style: const TextStyle(fontWeight: FontWeight.w600)),
                                  if (item.summary != null) Text(item.summary!, style: const TextStyle(height: 1.4)),
                                ],
                              ),
                            ),
                            StatusChip(statusLabel(item.status), tone: statusTone(item.status)),
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
}
