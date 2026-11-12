# 校园办事与入学助手 —— v1 API 与数据约定

本文是前后端共同契约。实现以 `/workspace/智慧校园助手/初版App方案.md` 为准；技术栈按 Light 锁定：学生/教师端 Flutter（Android+iOS，v1 不做小程序），管理端 Vue 3 + Element Plus，后端 FastAPI + PostgreSQL/pgvector + Redis + MinIO。

基址：服务端仅绑定 `127.0.0.1:8000`，经本机 Nginx 反向代理对外（先 HTTP，域名/HTTPS 未配）。所有业务路径以 `/api/v1` 为前缀。`GET /health` 保持根路径，供 compose 健康检查。

## 原则（不可破）

- 系统不代替学生确认、不代替老师审批；出单必须先过校验智能体。
- 知识回答固定三块：结论、依据、去办理/生成草稿。无依据不编造；无权限不漏正文。
- 规则在服务器，不打包进 App。App 不内置大模型；离线不回答模型问题；设备只缓存会话摘要与缩略图。安装包目标几十 MB，必须 < 1GB。
- 不绑定金蝶苍穹。不要改已锁定的演示台本（若仓库中尚无台本文件，不要新编一套对外台本冒充已锁定版本）。
- 不要把 `.env`、密码、密钥写入前端仓库或聊天。演示账号密码可写在 `docs/DEMO_ACCOUNTS.md`（仅演示口令，不是服务器密钥）。

## 角色

`student` | `teacher` | `counselor` | `admin`（admin 只用管理端）。

## 认证

- `POST /api/v1/auth/login` `{username, password}` → `{access_token, token_type, role, user}`
- Header: `Authorization: Bearer <jwt>`
- `GET /api/v1/me` 当前用户
- 演示账号（登录名 / 角色）：见 seed。密码统一放 DEMO_ACCOUNTS，不要用服务器 .env 里的库口令。

## 主要资源

### 档案
- `GET/PATCH /api/v1/me/profile` 基础字段：学号/工号、姓名、学院、专业、年级、班级、手机、邮箱、辅导员、宿舍、床位、紧急联系人
- `POST /api/v1/me/authorizations` 按这一次办事授权敏感项（银行卡、家庭经济、成绩、困难认定）。body: `{purpose, fields[], ref_type, ref_id?}`
- 未授权字段不得预填，确认页标注「未授权，未使用」

### 知识与对话（总管入口）
- `POST /api/v1/ask` `{text, attachments[]?}` 
  返回：
  ```
  {
    conversation_id,
    intent,
    answer: {
      conclusion,            # 短句结论；无依据时必须明确「知识库中没有找到相关规定」
      citations: [{document_id, chunk_id, filename, section, article, semester, quote, is_governing}],
      conflicts: [{chosen, other, reason}],
      action: {type, label, ref} | null,   # 去办理/生成草稿；纯查阅可为 null，改为转人工
      human_entry: {type, label} | null,
      permission_denied: bool              # true 时只提示需辅导员查看，citations 为空
    },
    slots_needed: [{field, question}] | []
  }
  ```
- `GET /api/v1/documents/{id}/chunks/{chunk_id}` 原文片段（供高亮）；无权限 403，不打码返回正文

总管只做理解、补全、分流、汇总。知识智能体检索（带身份过滤）。校验智能体走规则引擎。办事智能体在校验通过后才出草稿/单据。无 LLM Key 时：意图用规则+关键词，结论用检索片段抽取，禁止模型臆造条款。有 Key 时：模型只允许基于检索片段综述，每句结论可带 citation 角标。

### 待办与提醒
- `GET /api/v1/todos?status=` 首页待办（作业、报到、招募、请假确认/销假、奖助提醒、补件）。新生待办顶部可含 `group=enrollment`
- `GET /api/v1/reminders` 三类：`deadline|eligibility|anomaly`，含 citations 与 action
- `POST /api/v1/reminders/categories/{cat}/mute` 学生可关闭某一类提醒；待办仍保留。辅导员不可关闭本班异常。

### 请假
状态机：`draft | pending_confirm | submitted | approving | approved | pending_return | rejected | withdrawn | expired`

- `POST /api/v1/leaves` 一句话或附件发起（可先抽取再补全）
- `POST /api/v1/leaves/{id}/extract` 对照片做字段抽取，结果必须可改，不能直接当已校验材料
- `GET /api/v1/leaves/{id}` 含预填来源、校验结果、缺件列表、审批链、依据
- `POST /api/v1/leaves/{id}/confirm` **学生确认**后才提交。校验失败不得进入 submitted
- `POST /api/v1/leaves/{id}/withdraw` 仅审批前
- `POST /api/v1/leaves/{id}/return` 销假确认
- `GET /api/v1/approvals?type=leave` 审批箱
- `POST /api/v1/approvals/{id}/decide` `{decision: approve|reject|transfer, comment}` 驳回必填原因

规则（后台可调，默认）：短假 = 不超过 1 个自然日且不跨天，且不影响已登记考试 → 辅导员审。跨天或与考试/课堂冲突 → 加签（冲突本课则任课教师；无年级负责人时辅导员终审并备案）。材料不全当场拦住。有效期内附件可复用（缺日期默认 7 天）。

### 奖助 / 证明
- `GET /api/v1/aids/matches` 可能符合的项目（不够格不出现）。含匹配理由+条款。不自动提交。
- `POST /api/v1/aids/{program_id}/draft` 生成草稿（需授权）
- `POST /api/v1/aids/drafts/{id}/confirm` 学生确认。若无校级对接：状态 `confirmed_pending_submit`，提供材料包下载。
- 成绩/认定/授权变更后重算；过期或不再符合则撤提醒、草稿失效。
- 证明/补证走同一套：预审 → 拦缺件 → 确认页 → 提交；初版审批人默认辅导员。

### 任务（报到 / 作业 / 志愿者）
- 教师/辅导员 `POST /api/v1/tasks` `{type: registration|homework|volunteer, title, body, due_at, audience, ...}`
- 学生 `GET /api/v1/tasks/{id}` `POST /api/v1/tasks/{id}/submit` 或报名
- 志愿者不符合条件当场说明依据，不让提交
- 教师 `GET /api/v1/tasks/{id}/progress` 完成名单

### 管理端
- 用户/名单导入
- 规章入库（文件名、生效学期、适用角色、范围、是否优先文件）与切块校对
- 审批规则阈值
- 演示数据重置（仅演示环境）
- `GET /api/v1/admin/rules` `PUT /api/v1/admin/rules`

## 数据模型（核心表）

users, emergency_contacts, authorizations, documents, document_chunks (vector), conversations, messages, todos, reminders, reminder_mutes, leaves, leave_approvals, attachments, aid_programs, aid_matches, aid_drafts, tasks, task_assignees, task_submissions, audit_logs（检索文档ID、校验规则ID、是否出单；敏感字段不明文记入日志）。

## 错误约定

`{code, message, details?}`。缺件用 `code=validation_blocked` 且 `details.missing[]`。无权限知识用 `code=need_counselor`，body 不含条文。
