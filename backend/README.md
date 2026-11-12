# 校园办事与入学助手 · 后端

FastAPI + PostgreSQL/pgvector + Redis + MinIO。实现以 `/workspace/智慧校园助手/初版App方案.md` 和 `docs/API合同.md` 为准。

本地测试：

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

演示账号见 `docs/DEMO_ACCOUNTS.md`。不要把服务器 `.env` 或数据库口令写入本仓库。

生产部署时 API 只绑定 `127.0.0.1:8000`，经 Nginx 提供 `/health`、`/api/` 和 `/admin/`。
