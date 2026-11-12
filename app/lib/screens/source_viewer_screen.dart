import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../services/api_exception.dart';
import '../state/session.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class SourceViewerScreen extends StatefulWidget {
  const SourceViewerScreen({super.key, required this.citation});

  final Citation citation;

  @override
  State<SourceViewerScreen> createState() => _SourceViewerScreenState();
}

class _SourceViewerScreenState extends State<SourceViewerScreen> {
  DocumentChunk? _chunk;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final c = widget.citation;
    try {
      final chunk = await context.read<Session>().guard(
            () => context.read<Session>().api.getChunk(c.documentId, c.chunkId),
          );
      if (!mounted) return;
      setState(() {
        _chunk = chunk;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.needCounselor || e.isForbidden
            ? '该规定需辅导员查看。系统不会展示无权限正文。'
            : e.message;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.citation;
    return Scaffold(
      appBar: AppBar(title: const Text('原文')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
              children: [
                Text(c.filename, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                Text(
                  [c.clause, if (c.semester != null) c.semester!].where((e) => e.isNotEmpty).join(' · '),
                  style: const TextStyle(color: AppColors.muted),
                ),
                const SizedBox(height: 16),
                if (_error != null)
                  SoftCard(
                    color: AppColors.dangerSoft,
                    child: Text(_error!, style: const TextStyle(height: 1.5, color: AppColors.danger)),
                  )
                else if (_chunk != null)
                  SoftCard(child: _highlighted(_chunk!)),
              ],
            ),
    );
  }

  Widget _highlighted(DocumentChunk chunk) {
    final raw = chunk.text;
    final needle = chunk.highlight?.isNotEmpty == true ? chunk.highlight! : widget.citation.quote;
    if (needle.isEmpty || !raw.contains(needle)) {
      return Text(raw, style: const TextStyle(height: 1.7, fontSize: 15));
    }
    final i = raw.indexOf(needle);
    return Text.rich(
      TextSpan(
        style: const TextStyle(height: 1.7, fontSize: 15, color: AppColors.ink),
        children: [
          TextSpan(text: raw.substring(0, i)),
          TextSpan(
            text: needle,
            style: const TextStyle(
              backgroundColor: Color(0xFFC8EDE4),
              fontWeight: FontWeight.w600,
            ),
          ),
          TextSpan(text: raw.substring(i + needle.length)),
        ],
      ),
    );
  }
}
