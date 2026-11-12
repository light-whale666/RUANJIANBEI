export const ROLES = [
  { value: 'student', label: '学生' },
  { value: 'teacher', label: '任课教师' },
  { value: 'counselor', label: '辅导员/班主任' },
  { value: 'admin', label: '管理员' },
]

export const FRONT_ROLES = ROLES.filter((r) => r.value !== 'admin')

export const ROLE_LABEL = Object.fromEntries(ROLES.map((r) => [r.value, r.label]))

export const DOC_ROLES = [
  { value: 'student', label: '学生' },
  { value: 'teacher', label: '任课教师' },
  { value: 'counselor', label: '辅导员/班主任' },
]

export const DEFAULT_RULES = {
  short_leave_max_days: 1,
  short_leave_require_same_day: true,
  countersign_if_overnight: true,
  countersign_if_exam_conflict: true,
  countersign_if_class_conflict: true,
  attachment_valid_days_default: 7,
  counselor_final_if_no_grade_lead: true,
}

export const IMPORT_TEMPLATE_URL = `${import.meta.env.BASE_URL}templates/users-import-template.csv`
