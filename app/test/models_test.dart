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
            'filename': '学生请假管理办法',
            'article': '第十二条',
            'semester': '2026学年秋季学期',
            'is_governing': true,
          }
        ],
        'conflicts': [
          {'chosen': '以新办法为准', 'other': '旧办法', 'reason': '较新生效学期'}
        ],
        'action': {'type': 'leave', 'label': '去请假'},
        'permission_denied': false,
      }
    });
    expect(result.conclusion, '可以请假');
    expect(result.citations.single.isGoverning, isTrue);
    expect(result.conflicts.single.chosen, contains('新办法'));
    expect(result.action?.type, 'leave');
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
