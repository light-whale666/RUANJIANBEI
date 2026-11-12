import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/models.dart';
import '../theme/app_theme.dart';

final dateFmt = DateFormat('M月d日 HH:mm');
final dayFmt = DateFormat('M月d日');

String formatDue(DateTime? d) {
  if (d == null) return '';
  final now = DateTime.now();
  final onlyDay = DateTime(d.year, d.month, d.day);
  final today = DateTime(now.year, now.month, now.day);
  final diff = onlyDay.difference(today).inDays;
  if (d.hour == 0 && d.minute == 0) {
    if (diff == 0) return '今日截止';
    if (diff == 1) return '明日截止';
    if (diff < 0) return '${dayFmt.format(d)}已过期';
    return '${dayFmt.format(d)}截止';
  }
  if (diff == 0) return '今日 ${DateFormat('HH:mm').format(d)}';
  if (diff < 0) return '${dateFmt.format(d)}已过期';
  return dateFmt.format(d);
}

class SoftCard extends StatelessWidget {
  const SoftCard({super.key, required this.child, this.padding, this.color, this.onTap});

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final body = Container(
      width: double.infinity,
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color ?? AppColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.line),
      ),
      child: child,
    );
    if (onTap == null) return body;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: body,
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});

  final String text;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 8),
      child: Row(
        children: [
          Text(text, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.ink)),
          const Spacer(),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.title, this.subtitle, this.icon = Icons.inbox_outlined});

  final String title;
  final String? subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 24),
      child: Column(
        children: [
          Icon(icon, size: 36, color: AppColors.muted),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.ink)),
          if (subtitle != null) ...[
            const SizedBox(height: 6),
            Text(subtitle!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.muted, height: 1.4)),
          ],
        ],
      ),
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip(this.text, {super.key, this.tone = 'muted'});

  final String text;
  final String tone;

  @override
  Widget build(BuildContext context) {
    late Color bg, fg;
    switch (tone) {
      case 'good':
        bg = AppColors.successSoft;
        fg = AppColors.success;
        break;
      case 'warn':
        bg = AppColors.warningSoft;
        fg = AppColors.warning;
        break;
      case 'bad':
        bg = AppColors.dangerSoft;
        fg = AppColors.danger;
        break;
      case 'teal':
        bg = AppColors.tealSoft;
        fg = AppColors.tealDark;
        break;
      default:
        bg = AppColors.sand;
        fg = AppColors.muted;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
      child: Text(text, style: TextStyle(fontSize: 12, color: fg, fontWeight: FontWeight.w600)),
    );
  }
}

String statusLabel(String? status) {
  switch (status) {
    case 'draft':
      return '草稿';
    case 'pending_confirm':
      return '待确认';
    case 'submitted':
      return '已提交';
    case 'approving':
      return '审批中';
    case 'approved':
      return '已批准';
    case 'pending_return':
      return '待销假';
    case 'rejected':
      return '已驳回';
    case 'withdrawn':
      return '已撤回';
    case 'expired':
      return '已完成';
    case 'confirmed_pending_submit':
      return '草稿已确认，待报送';
    case 'pending':
      return '待处理';
    default:
      return status ?? '';
  }
}

String statusTone(String? status) {
  switch (status) {
    case 'approved':
    case 'expired':
    case 'confirmed_pending_submit':
      return 'good';
    case 'rejected':
      return 'bad';
    case 'pending_return':
    case 'pending_confirm':
    case 'approving':
    case 'pending':
      return 'warn';
    default:
      return 'muted';
  }
}

class ErrorBanner extends StatelessWidget {
  const ErrorBanner(this.message, {super.key, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.dangerSoft,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: AppColors.danger, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: const TextStyle(color: AppColors.danger, height: 1.35))),
          if (onRetry != null)
            TextButton(onPressed: onRetry, child: const Text('重试')),
        ],
      ),
    );
  }
}

class DemoBanner extends StatelessWidget {
  const DemoBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: AppColors.sand,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: const Text(
        '本地预览 · 未连接服务器，数据不会保存到云端',
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: 12, color: AppColors.ink),
      ),
    );
  }
}

class OfflineBanner extends StatelessWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: AppColors.warningSoft,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: const Text(
        '当前离线：不能回答知识问题。可查看已缓存的待办摘要。',
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: 12, color: AppColors.warning),
      ),
    );
  }
}

class CitationCard extends StatelessWidget {
  const CitationCard({super.key, required this.citation, this.index, this.onTap});

  final Citation citation;
  final int? index;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return SoftCard(
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: citation.isGoverning ? AppColors.tealSoft : AppColors.sand,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '${index ?? 1}',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                color: citation.isGoverning ? AppColors.tealDark : AppColors.muted,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(citation.filename, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                const SizedBox(height: 4),
                Text(
                  citation.subtitle.isEmpty ? '条款信息未标注' : citation.subtitle,
                  style: const TextStyle(color: AppColors.muted, fontSize: 12.5),
                ),
                if (citation.quote.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    citation.quote,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(height: 1.45, fontSize: 13, color: AppColors.ink),
                  ),
                ],
                const SizedBox(height: 6),
                Text(onTap == null ? '' : '查看原文高亮', style: const TextStyle(color: AppColors.teal, fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class ConflictBanner extends StatelessWidget {
  const ConflictBanner({super.key, required this.conflicts});

  final List<ConflictNote> conflicts;

  @override
  Widget build(BuildContext context) {
    if (conflicts.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.warningSoft,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE8D39A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('规定冲突：已写明以哪份为准', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.warning)),
          const SizedBox(height: 8),
          for (final c in conflicts) ...[
            Text(c.chosen, style: const TextStyle(height: 1.4, fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text('同时列出被搁置：${c.other}', style: const TextStyle(height: 1.4, color: AppColors.ink)),
            if (c.reason.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(c.reason, style: const TextStyle(color: AppColors.muted, height: 1.4, fontSize: 13)),
              ),
          ],
        ],
      ),
    );
  }
}

class TodoTile extends StatelessWidget {
  const TodoTile({super.key, required this.item, required this.onTap});

  final TodoItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SoftCard(
      onTap: onTap,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 4,
            height: 46,
            margin: const EdgeInsets.only(right: 12, top: 2),
            decoration: BoxDecoration(
              color: item.highPriority ? AppColors.warning : AppColors.teal,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, height: 1.3)),
                if (item.subtitle != null && item.subtitle!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(item.subtitle!, style: const TextStyle(color: AppColors.muted, height: 1.35)),
                ],
                if (item.dueAt != null) ...[
                  const SizedBox(height: 6),
                  Text(formatDue(item.dueAt), style: const TextStyle(fontSize: 12.5, color: AppColors.muted)),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(
            onPressed: onTap,
            style: FilledButton.styleFrom(
              minimumSize: const Size(72, 36),
              padding: const EdgeInsets.symmetric(horizontal: 12),
              textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
            child: Text(item.actionLabel),
          ),
        ],
      ),
    );
  }
}

class FieldTable extends StatelessWidget {
  const FieldTable({super.key, required this.fields, this.title});

  final List<FieldSource> fields;
  final String? title;

  @override
  Widget build(BuildContext context) {
    if (fields.isEmpty) return const SizedBox.shrink();
    return SoftCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title != null) ...[
            Text(title!, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 10),
          ],
          for (var i = 0; i < fields.length; i++) ...[
            if (i > 0) const Divider(height: 18),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 86,
                  child: Text(fields[i].label, style: const TextStyle(color: AppColors.muted, height: 1.4)),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        fields[i].value.isEmpty ? '—' : fields[i].value,
                        style: TextStyle(
                          height: 1.4,
                          color: fields[i].source == 'unauthorized' ? AppColors.muted : AppColors.ink,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(fields[i].sourceLabel, style: const TextStyle(fontSize: 12, color: AppColors.muted)),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
