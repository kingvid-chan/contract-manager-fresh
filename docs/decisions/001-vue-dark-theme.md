# ADR-001: Vue.js 3 前端迁移 + 暗色主题

## 状态

已接受 (2026-06-18)

## 背景

0.0.1 使用 FastAPI + Jinja2 服务端渲染，前端交互基于表单 POST 和页面跳转。老板提出 0.0.2 两条需求：

1. 「前端修改为 Vue」 — 将前端框架改为 Vue.js
2. 「页面样式主题修改为黑色」 — 暗色主题

## 决策

### 前端框架：Vue.js 3 CDN 加载

- **选择**：Vue.js 3（通过 CDN 引入，不引入构建工具链如 webpack/vite）
- **理由**：
  - 项目是演示级内部工具，无需构建工具链的复杂性
  - CDN 加载保持部署简单（无需 node_modules、npm build）
  - Vue 3 Composition API 支持更清晰的组件逻辑
  - 与现有 Python 后端完全解耦
- **替代方案**：
  - React CDN：需要 JSX 转译或 createElement，模板不如 Vue 直观
  - Alpine.js：功能不足以支撑 SPA 多页面路由
  - 保持 Jinja2 + HTMX：不满足老板"改为 Vue"的需求

### 路由：Vue Router hash mode

- **选择**：Hash mode（`#/path`）
- **理由**：
  - Hash 路由不需要服务端配合（无需 Nginx `try_files`）
  - 所有路由在 hash 后，浏览器不会发送到服务端，天然 SPA
  - FastAPI 只需返回 `index.html` 一个文件

### 主题：CSS 变量驱动的暗色主题

- **选择**：CSS 自定义属性（`--color-*`），暗色背景 `#1a1a2e`，文字 `#e0e0e0`
- **理由**：
  - CSS 变量可在 `:root` 统一切换，无需 Sass/Less
  - 暗色配色方案减少眩光，适合长时间使用
  - 强调色（蓝色 `#60a5fa`）保持 WCAG AA 对比度
- **配色方案**：
  - 背景：`#1a1a2e`（主背景）、`#16213e`（卡片/面板）
  - 文字：`#e0e0e0`（主文字）、`#a0aec0`（次要文字）
  - 边框：`#2d3748`
  - 主色：`#60a5fa`
  - 成功：`#4ade80`、警告：`#fbbf24`、危险：`#f87171`

### 后端：新增 JSON API 路由

- **选择**：新增 `app/api/` 包，所有端点返回 JSON
- **理由**：
  - 保持 0.0.1 的 Jinja2 路由完全不变（向后兼容）
  - 新 API 返回 `application/json`，方便 Vue SPA fetch 调用
  - 如果未来需要纯 API 服务，可直接复用
- **API 前缀**：`/projects/contract-manager-fresh/api/`

### SPA 入口文件

- **位置**：`app/static/spa/index.html`
- **服务方式**：FastAPI 对所有非 API/非静态路径返回此文件（SPA fallback）
- **组件**：所有 Vue 组件定义在 `app/static/spa/js/app.js`（单文件），暗色主题在 `app/static/spa/css/theme.css`

## 后果

### 正面

- 前端交互更流畅（SPA 无页面刷新）
- 前后端分离，各自可独立演进
- 暗色主题改善用户体验
- 无需 Node.js 构建工具链

### 负面

- 单文件 Vue 组件随着功能增加会变长
- 无 TypeScript 类型检查
- CDN 依赖外部网络（可后续添加本地 fallback）

### 风险缓解

- 如果 CDN 不可用，可在部署时将 Vue 文件放入 static 目录
- 单文件 JS 可按功能域拆分为多个文件（auth.js, contracts.js 等）

## 关联

- 迭代文档：`docs/iterations/0.0.2.md`
- 架构文档：`docs/architecture.md`
