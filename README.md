# 墨刊 · 个人博客

一个**用 Flask 手工搭建**的个人博客——从数据模型、路由、模板到样式全部自己实现，
没有套用任何博客系统。定位是学习 + 作品集项目，展示一条完整的 Python Web 技术线。

## 特性

- **前台**：首页时间轴刊列、文章详情（Markdown 渲染 + 代码高亮）、标签筛选、按年归档、RSS 订阅、阅读计数、上下篇导航
- **后台**：登录鉴权、文章增删改查、草稿 / 发布状态管理（未发布文章前台 404）
- **视觉**：「墨刊」纸质期刊设计——米纸底色、朱砂点缀、宋体标题、深浅色模式切换
- **工程**：Blueprint 前后台分层、应用工厂、幂等建表 + 种子数据、14 个单元测试

## 目录结构

```
flask-blog/
├── app.py            # 应用工厂、Markdown 过滤器、启动入口
├── models.py         # 数据访问层 (建表、种子、文章 CRUD)
├── views.py          # 前台蓝图 (首页/详情/标签/归档/RSS)
├── admin_views.py    # 后台蓝图 (登录、文章管理, 全部要求鉴权)
├── templates/        # Jinja2 模板 (含 admin/ 子目录)
├── static/css/       # 全站样式 + Pygments 高亮主题
├── tests/            # 单元测试
└── requirements.txt
```

## 快速开始

环境要求：Python 3.11（3.9+ 均可）。

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows; Linux/macOS 用 source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

启动后访问 <http://127.0.0.1:5000>，首次运行自动建库并写入演示文章。

| 入口     | 地址                            | 账号           |
| -------- | ------------------------------- | -------------- |
| 前台     | <http://127.0.0.1:5000>         | 无需登录       |
| 管理后台 | <http://127.0.0.1:5000/admin/>  | admin / admin123 |

## 运行测试

```bash
python -m unittest discover -s tests -t . -v
```

测试使用临时数据库，不会污染开发库 `blog.db`。

## 配置（环境变量）

| 变量                | 说明                                       | 默认值          |
| ------------------- | ------------------------------------------ | --------------- |
| `BLOG_SECRET_KEY`   | 会话密钥，**生产环境必须设为随机值**       | 开发用固定值    |
| `BLOG_ADMIN_PASSWORD` | 管理员初始密码（仅首次建库生效）         | `admin123`      |
| `BLOG_DB`           | 数据库文件路径                             | 项目根目录      |
| `BLOG_SEED_POSTS`   | 置 `0` 时不写入演示文章                    | （写入演示文章）|

## 技术要点

- **存储**：SQLite + 原生 SQL，无 ORM；标签以 `,tag1,tag2,` 规整存储，精确匹配查询
- **渲染**：Python-Markdown（`extra` + `codehilite` + `toc`），Pygments 生成高亮主题
- **鉴权**：服务端会话 + Werkzeug 密码哈希，`login_required` 只出现在后台模块
- **安全**：HttpOnly + SameSite=Lax Cookie；文章仅管理员可写（若开放投稿需加 HTML 消毒）

## 部署提示

生产部署时设置环境变量后使用 WSGI 服务器，例如：

```bash
set BLOG_SECRET_KEY=请换成随机值
pip install waitress
waitress-serve --port=8000 app:app
```
