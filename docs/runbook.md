# Contract Manager 运行手册 v0.0.2

## 本地安装与启动

```bash
# 使用项目 run.sh 脚本
bash run.sh

# 或手动启动
~/外部需求/.conda/codingagent/bin/pip install -r requirements.txt
~/外部需求/.conda/codingagent/bin/python seeds/seed.py
~/外部需求/.conda/codingagent/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 测试、构建与健康检查

```bash
# 运行全部自测
~/外部需求/.conda/codingagent/bin/python -m pytest tests/test_self.py -v

# 测试通过条件: 85 passed
```

## 环境变量

| Variable | Default | Description |
|---|---|---|
| `APP_VERSION` | 0.0.2 | 应用版本 |
| `VERSION_TOKEN` | 0.0.2 | 静态资源版本令牌 |
| `DATABASE_URL` | sqlite:///./data/contract_manager.db | 数据库 URL |
| `SECRET_KEY` | dev-secret-change-in-production | Session 密钥 |
| `UPLOAD_DIR` | ./uploads | 附件存储目录 |

## Base Path

项目 base path: `/projects/contract-manager-fresh/`

- 前端 SPA: `GET /projects/contract-manager-fresh/` → `spa/index.html`
- JSON API: `/projects/contract-manager-fresh/api/*`
- SSR 路由: `/projects/contract-manager-fresh/auth/*`, `/projects/contract-manager-fresh/contracts/*`, etc.
- 静态资源: `/projects/contract-manager-fresh/static/*`

## 缓存策略

- HTML 响应头: `Cache-Control: no-cache, no-store, must-revalidate`
- 静态资源 URL: `?v=0.0.2` 版本令牌
- 所有资源路径保留 `/projects/contract-manager-fresh/` 前缀

## 公网浏览器验收

1. 访问 `https://<domain>/projects/contract-manager-fresh/`
2. Vue SPA 加载，自动导航到 `/#/login`
3. 演示账号: admin/admin123, user/user123
4. HTML 响应 `Cache-Control: no-cache` 头
5. 静态资源带 `?v=0.0.2` 令牌

## 日志查看

应用日志输出到 stdout。操作审计日志存储在 `audit_logs` 表，通过 SPA 的 "操作日志" 页面查看。

## 回滚

```bash
# 回滚到 0.0.1
git checkout tags/v0.0.1
bash run.sh
```
