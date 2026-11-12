import 'package:campus_assistant/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('AskResult 解析结论、依据、冲突与办理入口', () {
    final result = AskResult.fromJson({
      'conversation_id': 'c1',
      'intent': 'leave',
      'answer': {
        'conclusion': '可以请假',
        'citations': [
          {
            'document_id': 'd1',
            'chunk_id': 'k1',
            'filename': '【模板示例】学生请假管理规定',
            'article': '第二条 【示例】短假',
            'semester': '【示例】2025-2026学年',
            'is_governing': true,
          }
        ],
        'conflicts': [
          {'chosen': '以新办法为准', 'other': '旧办法', 'reason': '较新生效学期'}
        ],
        'action': {'type': 'leave', 'label': '去请假'},
        'permission_denied': false,
      },
      'decision': {
        'path': 'leave.draft_and_confirm',
        'intent': 'leave',
        'confidence': 0.84,
        'uncertain': false,
        'source': 'rules',
        'steps': [
          {'id': 'decide.select', 'action': 'select_path', 'reason': '采用请假路径', 'evidence': ['leave:0.84']}
        ],
        'why_confirm': '必须由学生本人确认',
        'awaiting': 'student_confirm',
        'knowledge_scope': ['leave'],
        'prefill': {'used': ['name'], 'skipped_unauthorized': []}
      }
    });
    expect(result.conclusion, '可以请假');
    expect(result.citations.single.isGoverning, isTrue);
    expect(result.citations.single.filename, contains('【模板示例】'));
    expect(result.conflicts.single.chosen, contains('新办法'));
    expect(result.action?.type, 'leave');
    expect(result.decision?.path, 'leave.draft_and_confirm');
    expect(result.decision?.source, 'rules');
    expect(result.decision?.awaiting, 'student_confirm');
    expect(result.decision?.whyConfirm, contains('学生本人确认'));
    expect(result.decision?.steps.single.reason, contains('请假路径'));
  });

  test('无权限回答不携带正文依据', () {
    final result = AskResult.fromJson({
      'conversation_id': 'c2',
      'answer': {
        'conclusion': '该规定需辅导员查看',
        'citations': [],
        'permission_denied': true,
        'human_entry': {'type': 'counselor', 'label': '转给辅导员'},
      }
    });
    expect(result.permissionDenied, isTrue);
    expect(result.citations, isEmpty);
  });
}
