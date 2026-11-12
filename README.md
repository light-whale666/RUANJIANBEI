# 智慧校园助手（第一版）

师生共用的校园办事与入学助手。学生可以按引用查看校园规章、一键预填资料、申请请假，并收到奖助预审提醒；教师和辅导员负责发布任务与审批。系统不会代替学生确认或教师审批。

## 技术栈

- 学生端 / 教师端：Flutter（Android + iOS；第一版不含微信小程序）
- 管理端：Vue 3 + Element Plus
- 后端：Python FastAPI、PostgreSQL（pgvector）、Redis、MinIO

学生端安装包控制在 1 GB 以内（当前 Android 包约 56 MB，未打入模型）。业务数据和问答都在云端完成。

## 仓库结构

- `app/`：Flutter 客户端
- `admin/`：管理端
- `backend/`：FastAPI 后端
- `docs/`：接口说明、演示账号和初版方案

## 演示账号

统一演示口令见 `docs/DEMO_ACCOUNTS.md`。这些只用于演示登录，不是服务器或数据库密钥。

知识库默认为空，须先在管理端导入模板示例或上传校方文档后才能检索；未导入时问答不会编造条款。建议演示顺序见 `docs/DEMO_ACCOUNTS.md`。总管会在问答结果中展示决策路径、依据和为何要确认。

## 运行说明

本地构建和部署步骤见各目录下的 README：

- [后端](backend/README.md)
- [管理端](admin/README.md)
- [Flutter 客户端](app/README.md)

默认演示 API 地址是 `http://8.148.186.220`。请不要把服务器上的 `.env` 或真实密钥提交进仓库。
