# 校园办事与入学助手 · 管理后台

管理员专用 Web 端（不进学生 / 教师 App）。技术栈：Vue 3 + Vite + Element Plus。

本目录只包含前端。不要把服务器 `.env`、数据库口令或其它密钥写入本仓库。

## 功能

- 登录（JWT，仅 `admin` 角色可进入）
- 名单导入 / 用户与班级归属
- 规章入库：上传 PDF / Word / 文本，填写文件名、生效学期、适用角色、适用范围、是否优先文件；切块列表可校对
- 审批规则：短假阈值、加签条件、材料有效期默认天数
- 演示数据重置（二次确认：对话框 + 输入「确认重置」）

## 本地开发

```bash
cd admin
pnpm install
pnpm dev
```

开发服务器在 `http://127.0.0.1:5173/admin/`。

默认 `VITE_API_BASE=http://8.148.186.220`（请求发往 `/api/v1`）。若浏览器报 CORS，把 `.env.development` 里的 `VITE_API_BASE` 改为空，请求会走 Vite 代理到 `VITE_DEV_PROXY_TARGET`。

## 构建

```bash
cd admin
pnpm install
pnpm build
```

产物在 `admin/dist/`，已按 `/admin/` 公共路径打包。

## 部署（Nginx 就绪后）

当前 ECS（`8.148.186.220`）上 API 只绑 `127.0.0.1:8000`，系统 Nginx **尚未启用**（80/443 未监听）。因此构建产物先留在仓库，待 Nginx 配置后再发布。

建议步骤：

1. 在本机执行 `pnpm build`。
2. 将 `dist/` 同步到服务器 `/opt/campus-assistant/www/admin/`：

   ```bash
   ssh root@8.148.186.220 'mkdir -p /opt/campus-assistant/www/admin'
   rsync -a --delete dist/ root@8.148.186.220:/opt/campus-assistant/www/admin/
   ```

3. 使用 `deploy/nginx-campus-assistant.conf` 作为站点配置样例（监听 80，提供 `/admin/`，并把 `/api/`、`/health` 反代到 `127.0.0.1:8000`）。
4. 访问：`http://8.148.186.220/admin/`

**不要**：覆盖 `/opt/campus-assistant/.env`；把 5432 / 6379 / 9000 对公网开放；改动 chatgpt-lite（8080）与 ollama（11435）。

## 前端调用的管理端 API

契约原文对管理端只明确了登录、`/me` 和审批规则路径。下列路径是本管理端按方案补全的约定，后端应对齐；若最终实现有差异，只需改 `src/api/`。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/login` | `{username, password}` → `{access_token, token_type, role, user}` |
| GET | `/api/v1/me` | 当前用户，用于校验仍为 admin |
| GET | `/api/v1/admin/stats` | 可选。概览数字；没有则忽略 |
| GET | `/api/v1/admin/users` | 查询参数：`role,q,college,class_name,page,page_size`；返回 `{items,total,page,page_size}` |
| POST | `/api/v1/admin/users` | 新建用户 |
| PATCH | `/api/v1/admin/users/{id}` | 更新用户或班级归属 |
| POST | `/api/v1/admin/users/import` | `multipart/form-data`，字段 `file`（CSV）。返回 `{created,updated,errors:[{row,message}]}` |
| GET | `/api/v1/admin/documents` | 查询参数：`q,semester,page,page_size`；返回 `{items,total,page,page_size}` |
| POST | `/api/v1/admin/documents` | `multipart`：`file` + `filename,semester,roles,scope,is_priority`（后三项可为 JSON 字符串） |
| GET | `/api/v1/admin/documents/{id}` | 规章详情 |
| PATCH | `/api/v1/admin/documents/{id}` | 更新元数据（不含替换文件） |
| GET | `/api/v1/admin/documents/{id}/chunks` | 切块列表 `{items}` |
| PATCH | `/api/v1/admin/documents/{id}/chunks/{chunk_id}` | 校对单条切块 |
| PUT | `/api/v1/admin/documents/{id}/chunks` | 可选批量保存 `{chunks:[]}` |
| GET | `/api/v1/admin/rules` | 审批规则 |
| PUT | `/api/v1/admin/rules` | 更新审批规则 |
| POST | `/api/v1/admin/demo/reset` | `{confirm:true}`，仅演示环境 |

### 审批规则字段

```json
{
  "short_leave_max_days": 1,
  "short_leave_require_same_day": true,
  "countersign_if_overnight": true,
  "countersign_if_exam_conflict": true,
  "countersign_if_class_conflict": true,
  "attachment_valid_days_default": 7,
  "counselor_final_if_no_grade_lead": true
}
```

### 规章元数据

- `filename`：文件名
- `semester`：生效学期，如 `2026-2027-1`
- `roles`：`student` / `teacher` / `counselor` 数组
- `counselor_only`：仅辅导员内部（学生检索不回正文）
- `scope`：`{"type":"all"}` 或 `{"type":"colleges","colleges":["计算机学院"]}`
- `is_priority`：冲突时的优先文件

错误体约定：`{code, message, details?}`。
