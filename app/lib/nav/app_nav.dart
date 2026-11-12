import 'package:flutter/material.dart';

import '../models/models.dart';
import '../screens/aid_draft_screen.dart';
import '../screens/approval_detail_screen.dart';
import '../screens/ask_result_screen.dart';
import '../screens/confirm_screen.dart';
import '../screens/leave_compose_screen.dart';
import '../screens/leave_detail_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/progress_screen.dart';
import '../screens/source_viewer_screen.dart';
import '../screens/task_detail_screen.dart';
import '../state/session.dart';

class AppNav {
  static Future<T?> push<T>(BuildContext context, Widget page) {
    return Navigator.of(context).push<T>(MaterialPageRoute(builder: (_) => page));
  }

  static Future<void> openCitation(BuildContext context, Citation c) {
    return push(context, SourceViewerScreen(citation: c));
  }

  static Future<void> openAskResult(
    BuildContext context, {
    required AskResult result,
    required String question,
  }) {
    return push(context, AskResultScreen(result: result, question: question));
  }

  static Future<void> openTodo(BuildContext context, Session session, TodoItem item) {
    return openAction(
      context,
      type: item.actionType ?? item.type,
      refId: item.refId ?? item.id,
      refType: item.refType,
    );
  }

  static Future<void> openAction(
    BuildContext context, {
    String? type,
    String? refId,
    String? refType,
  }) async {
    final t = (type ?? refType ?? '').toLowerCase();
    if (t.contains('profile')) {
      await push(context, const ProfileScreen());
      return;
    }
    if (t.contains('approval')) {
      if (refId != null) {
        await push(context, ApprovalDetailScreen(approvalId: refId));
      }
      return;
    }
    if (t.contains('progress')) {
      if (refId != null) await push(context, ProgressScreen(taskId: refId));
      return;
    }
    if (t.contains('leave_return') || t == 'return') {
      if (refId != null) {
        await push(context, LeaveDetailScreen(leaveId: refId, startInReturn: true));
      }
      return;
    }
    if (t.contains('leave')) {
      if (refId != null) {
        await push(context, LeaveDetailScreen(leaveId: refId));
      } else {
        await push(context, const LeaveComposeScreen());
      }
      return;
    }
    if (t.contains('aid') || t.contains('scholarship')) {
      await push(context, AidDraftScreen(programOrDraftId: refId ?? 'aid_lizhi'));
      return;
    }
    if (t.contains('certificate') || t.contains('证明') || t.contains('补证')) {
      await push(context, LeaveComposeScreen(presetReason: '补办学生证 / 开具证明', asCertificate: true));
      return;
    }
    if (t.contains('task') ||
        t.contains('homework') ||
        t.contains('volunteer') ||
        t.contains('registration') ||
        t.contains('signup')) {
      if (refId != null) {
        await push(context, TaskDetailScreen(taskId: refId));
      }
      return;
    }
    if (refId != null && (t.isEmpty || t.contains('todo'))) {
      await push(context, TaskDetailScreen(taskId: refId));
    }
  }

  static Future<bool> openConfirm(
    BuildContext context, {
    required ConfirmPayload payload,
    required Future<void> Function() onConfirm,
  }) async {
    final ok = await push<bool>(
      context,
      ConfirmScreen(payload: payload, onConfirm: onConfirm),
    );
    return ok == true;
  }
}
