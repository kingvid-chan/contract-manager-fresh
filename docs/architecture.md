# Contract Manager 当前架构 (v0.0.2)

## 系统目标与边界

企业内部合同管理系统，演示用途。支持合同全生命周期管理（创建、审批流、执行、终止）、用户管理、附件管理和操作审计。

## 技术栈与选择理由

| 层 | 技术 | 理由 |
|---|---|---|
| 后端 | FastAPI 0.115 | Python 异步框架，类型安全 |
| 前端 (SPA) | Vue.js 3 CDN + Vue Router hash mode | 无构建工具链，CDN 加载，hash 路由免服务端配置 |
| 前端 (SSR) | Jinja2 3.1 | 0.0.1 遗留，保持向后兼容 |
| 数据库 | SQLite + SQLAlchemy 2.0 | 开发/演示环境，零配置 |
| 认证 | 服务端 Session (itsdangerous) | Cookie-based，无需 Token 管理 |
| 密码 | bcrypt (passlib) | 安全的单向哈希 |

## 模块职责与依赖

```
app/
├── main.py          — 应用入口：中间件、路由注册、SPA fallback
├── config.py        — 环境变量配置 (Pydantic Settings)
├── database.py      — SQLAlchemy 引擎、Session、Base
├── models/          — ORM 模型 (User, Contract, Attachment, AuditLog)
├── routers/         — SSR 路由 (Jinja2, 0.0.1 遗留，backward-compatible)
├── api/             — JSON API 路由 (Vue SPA 消费, 0.0.2 新增)
├── services/        — 业务逻辑层 (auth, user, contract, audit)
├── schemas/         — Pydantic 数据模型
├── static/
│   ├── css/         — SSR 样式 (0.0.1 遗留)
│   ├── js/          — SSR JS (0.0.1 遗留)
│   └── spa/         — Vue SPA 静态文件 (0.0.2 新增)
│       ├── index.html
│       ├── css/theme.css  — 暗色主题
│       └── js/app.js      — Vue 应用
└── templates/       — Jinja2 模板 (0.0.1 遗留)
```

## 数据流

```
浏览器 → /projects/contract-manager-fresh/
       → FastAPI 返回 spa/index.html
       → Vue Router 接管 hash 路由 (/#/contracts, etc.)
       → Vue 组件通过 fetch 调用 /api/* JSON 端点
       → FastAPI 返回 JSON
       → Vue 响应式更新 DOM
```

## API 设计

### JSON API (Vue SPA 使用)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login` | 登录 → JSON |
| GET | `/api/auth/me` | 当前用户 → JSON |
| POST | `/api/auth/logout` | 退出 → JSON |
| GET | `/api/contracts` | 合同列表 → JSON |
| GET | `/api/contracts/{id}` | 合同详情 → JSON |
| POST | `/api/contracts` | 创建合同 → JSON |
| PUT | `/api/contracts/{id}` | 编辑合同 → JSON |
| DELETE | `/api/contracts/{id}` | 删除合同 → JSON |
| POST | `/api/contracts/{id}/status` | 状态流转 → JSON |
| GET | `/api/users` | 用户列表 (admin) → JSON |
| POST | `/api/users` | 创建用户 (admin) → JSON |
| PUT | `/api/users/{id}` | 编辑用户 (admin) → JSON |
| DELETE | `/api/users/{id}` | 删除用户 (admin) → JSON |
| POST | `/api/users/{id}/toggle-status` | 启/禁用用户 (admin) → JSON |
| POST | `/api/users/{id}/reset-password` | 重置密码 (admin) → JSON |
| GET | `/api/audit-logs` | 操作日志 (admin) → JSON |
| POST | `/api/attachments/contracts/{id}` | 上传附件 → JSON |
| GET | `/api/attachments/{id}/download` | 下载附件 (file) |
| DELETE | `/api/attachments/{id}` | 删除附件 → JSON |

### SSR 路由 (0.0.1 遗留，backward-compatible)

保留全部 0.0.1 Jinja2 路由，行为不变。

## 前端路由 (Vue Router hash mode)

| Hash Route | Component | Auth |
|---|---|---|
| `#/login` | LoginPage | public |
| `#/` | Dashboard | authenticated |
| `#/contracts/:id` | ContractDetail | authenticated |
| `#/contracts/new` | ContractEdit | authenticated |
| `#/contracts/:id/edit` | ContractEdit | authenticated |
| `#/users` | UserList | admin |
| `#/users/new` | UserEdit | admin |
| `#/users/:id/edit` | UserEdit | admin |
| `#/audit-logs` | AuditLogs | admin |

## 暗色主题

CSS 变量驱动，配色：
- 主背景: `#1a1a2e` / 卡片: `#16213e` / 面板: `#1e2a45`
- 主文字: `#e0e0e0` / 次要: `#a0aec0`
- 强调色: `#60a5fa` (蓝), `#4ade80` (绿), `#fbbf24` (黄), `#f87171` (红)

## 测试策略

- 85 个 pytest 测试，覆盖 SSR + JSON API + 静态资源
- 数据库使用独立 SQLite (`data/test_contract_manager.db`)
- 每次运行前清空重建

## 部署拓扑

单进程 FastAPI + uvicorn，无反向代理。演示环境 `run.sh` 启动。

## 安全边界

- 服务端 Session 认证
- 密码 bcrypt 哈希
- 附件类型/大小校验
- 用户状态流转防护（不可自禁用/自删除）
- 合同状态机校验

## 已知技术债

- Vue 组件单文件化（当前所有组件在一个 JS 文件）
- SSR 路由可逐步下线
- 附件存储未去重

## 关联 ADR 与最近变更

- [ADR-001: Vue.js 3 前端迁移 + 暗色主题](decisions/001-vue-dark-theme.md)
- v0.0.2: Vue SPA, dark theme, JSON API
- v0.0.1: FastAPI + Jinja2 SSR, SQLite
