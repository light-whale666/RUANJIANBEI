import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../nav/app_nav.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _ask = TextEditingController();
  final _picker = ImagePicker();
  XFile? _photo;
  List<TodoItem> _todos = [];
  bool _loading = true;
  String? _error;
  bool _asking = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _ask.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final session = context.read<Session>();
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await session.guard(() => session.api.todos());
      await session.cacheTodos(items);
      if (!mounted) return;
      setState(() {
        _todos = items;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
        if (e.isOffline) {
          _todos = session.cachedTodoSummary().map((m) {
            return TodoItem(
              id: '${m['id']}',
              type: '${m['type'] ?? 'task'}',
              title: '${m['title'] ?? ''}',
              dueAt: DateTime.tryParse('${m['due_at'] ?? ''}'),
              actionLabel: '查看',
            );
          }).toList();
        }
      });
    }
  }

  Future<void> _pick(ImageSource source) async {
    final file = await _picker.pickImage(source: source, imageQuality: 85);
    if (file != null) setState(() => _photo = file);
  }

  Future<void> _submitAsk() async {
    final text = _ask.text.trim();
    if (text.isEmpty && _photo == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('请先输入问题，或附上假条/病例照片。')));
      return;
    }
    final session = context.read<Session>();
    if (!session.demoMode && !session.online) {
      showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('当前离线'),
          content: const Text('离线时不能回答知识问题。请联网后再问，或查看已缓存的待办摘要。'),
          actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('知道了'))],
        ),
      );
      return;
    }
    setState(() => _asking = true);
    try {
      final ids = <String>[];
      if (_photo != null) {
        final att = await session.guard(() => session.api.uploadAttachment(_photo!.path, filename: _photo!.name));
        ids.add(att.id);
      }
      final question = text.isEmpty ? '请根据我上传的材料，看看怎么办理。' : text;
      final result = await session.guard(() => session.api.ask(text: question, attachmentIds: ids));
      await session.rememberConversation(
        id: result.conversationId,
        question: question,
        conclusion: result.conclusion,
      );
      if (!mounted) return;
      _ask.clear();
      setState(() => _photo = null);
      await AppNav.openAskResult(context, result: result, question: question);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _asking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final name = session.user?.name ?? '同学';
    final freshman = session.user?.isFreshman == true;
    final enroll = _todos.where((t) => t.isEnrollment).toList();
    final rest = _todos.where((t) => !t.isEnrollment).toList();

    return RefreshIndicator(
      onRefresh: _load,
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('你好，$name', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(
                    freshman ? '先把入学与报到办完，有问题直接问一句。' : '要办的事都在待办里，也可以直接问。',
                    style: const TextStyle(color: AppColors.muted),
                  ),
                  const SizedBox(height: 16),
                  _askBox(),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    ErrorBanner(_error!, onRetry: _load),
                  ],
                ],
              ),
            ),
          ),
          if (_loading)
            const SliverFillRemaining(child: Center(child: CircularProgressIndicator()))
          else ...[
            if (freshman && enroll.isNotEmpty) ...[
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.fromLTRB(20, 20, 20, 0),
                  child: SectionTitle('入学与报到'),
                ),
              ),
              _todoSliver(session, enroll),
            ],
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: SectionTitle(rest.isEmpty && enroll.isEmpty ? '待办' : (freshman ? '其他待办' : '待办')),
              ),
            ),
            if (rest.isEmpty && (!freshman || enroll.isEmpty))
              const SliverToBoxAdapter(child: EmptyView(title: '暂时没有待办', subtitle: '作业、招募、请假和奖助都会出现在这里。'))
            else
              _todoSliver(session, rest),
            const SliverToBoxAdapter(child: SizedBox(height: 32)),
          ],
        ],
      ),
    );
  }

  Widget _todoSliver(Session session, List<TodoItem> items) {
    return SliverPadding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 0),
      sliver: SliverList.separated(
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, i) => TodoTile(
          item: items[i],
          onTap: () async {
            await AppNav.openTodo(context, session, items[i]);
            _load();
          },
        ),
      ),
    );
  }

  Widget _askBox() {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        children: [
          TextField(
            controller: _ask,
            minLines: 1,
            maxLines: 4,
            textInputAction: TextInputAction.send,
            onSubmitted: (_) => _submitAsk(),
            decoration: const InputDecoration(
              hintText: '有什么要办或要问的？例如：明天上午去医院，怎么请假',
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              filled: false,
              contentPadding: EdgeInsets.fromLTRB(4, 8, 4, 8),
            ),
          ),
          if (_photo != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  const Icon(Icons.image_outlined, size: 16, color: AppColors.teal),
                  const SizedBox(width: 6),
                  Expanded(child: Text(_photo!.name, overflow: TextOverflow.ellipsis)),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: () => setState(() => _photo = null),
                    icon: const Icon(Icons.close, size: 16),
                  ),
                ],
              ),
            ),
          Row(
            children: [
              IconButton(
                tooltip: '拍摄假条或病例',
                onPressed: () => _pick(ImageSource.camera),
                icon: const Icon(Icons.photo_camera_outlined),
              ),
              IconButton(
                tooltip: '从相册选择',
                onPressed: () => _pick(ImageSource.gallery),
                icon: const Icon(Icons.image_outlined),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _asking ? null : _submitAsk,
                style: FilledButton.styleFrom(minimumSize: const Size(88, 40)),
                child: _asking
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('提问'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
