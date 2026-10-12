# -*- coding: utf-8 -*-
"""数据访问层: SQLite 建表、初始化与文章 CRUD。

设计说明:
    1. tags 以 ",标签1,标签2," 形式存储, 查询时精确匹配 ",tag,",
       避免 LIKE 通配符与前缀误匹配。
    2. 读者端只返回 status='published' 的文章, 草稿仅后台可见。
    3. 数据库文件默认为项目根目录 blog.db, 可用环境变量 BLOG_DB 覆盖
       (单元测试用它指向临时库, 互不污染)。
"""
import os
import sqlite3
from datetime import datetime, timedelta

from flask import g
from werkzeug.security import check_password_hash, generate_password_hash

# 数据库文件路径: 环境变量可覆盖, 便于测试隔离
DB_PATH = os.environ.get("BLOG_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "blog.db"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    summary    TEXT NOT NULL DEFAULT '',
    content    TEXT NOT NULL,
    tags       TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'draft',   -- draft | published
    views      INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
"""


def normalize_tags(raw):
    """把逗号分隔的标签串规整为 ",tag1,tag2," 形式, 便于精确查询"""
    tags = [t.strip() for t in (raw or "").replace("，", ",").split(",")]
    tags = [t for t in tags if t]
    seen, ordered = set(), []
    for t in tags:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(t)
    return "," + ",".join(ordered) + "," if ordered else ""


def get_db():
    """获取当前请求上下文中的数据库连接, 首次调用时建立并绑定到 g"""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exc):
    """请求结束时关闭连接, 避免泄漏"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ----------------------------- 初始化与种子数据 -----------------------------
def _seed_users(db):
    """内置管理员账号: admin / admin123 (可用环境变量覆盖密码)"""
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return
    password = os.environ.get("BLOG_ADMIN_PASSWORD", "admin123")
    db.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("admin", generate_password_hash(password)),
    )


def _seed_posts(db):
    """首次运行写入演示文章, 让站点不空; BLOG_SEED_POSTS=0 可关闭"""
    if os.environ.get("BLOG_SEED_POSTS") == "0":
        return
    if db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]:
        return
    now = datetime.now()
    samples = [
        (
            "你好，墨刊",
            "博客开篇：为什么又造一个博客轮子，以及本站支持的 Markdown 能力演示。",
            """## 开篇

这是「墨刊」的第一篇文章。本站是一个用 **Flask + SQLite** 手写的个人博客，
源码在 [GitHub](https://github.com) 上公开。

### Markdown 支持演示

> 引用：写作是为了把想法钉在纸上。

有序列表：

1. 标题与目录
2. 代码高亮
3. 标签与归档

行内代码 `print("hello")` 与 Python 代码块：

```python
def fib(n: int) -> int:
    \"\"\"斐波那契，递归版仅供演示\"\"\"
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

表格：

| 特性 | 状态 |
| ---- | ---- |
| Markdown 渲染 | 已完成 |
| 代码高亮 | 已完成 |
| 管理后台 | 已完成 |
""",
            "博客,开篇",
            "published",
            now,
        ),
        (
            "Flask 蓝图实践笔记",
            "把前台与后台拆成两个 Blueprint，路由组织清晰了，测试也好写了。",
            """## 为什么用 Blueprint

单文件应用超过几百行后，路由、表单、模板混在一起会越来越难维护。
Blueprint 相当于"可挂载的子应用"：

```python
from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("/")
def dashboard():
    return "后台首页"
```

### 挂载到主应用

```python
app.register_blueprint(admin_bp)
```

### 我的划分方式

- `views.py` —— 读者可见的前台
- `admin_views.py` —— 需要登录的后台

这样权限边界一目了然：`login_required` 装饰器只出现在后台模块里。
""",
            "Flask,Python",
            "published",
            now - timedelta(days=3),
        ),
        (
            "SQLite 用在个人博客刚刚好",
            "别小看 SQLite：单机博客场景下它比 MySQL 更省心。",
            """## 单机站点的最优解

个人博客的读写量很低，SQLite 的优势很明显：

- **零运维**：没有独立进程，备份就是拷贝一个文件
- **事务安全**：WAL 模式下并发读完全够用
- **SQL 直写**：不需要 ORM 也能把查询写得清清楚楚

```sql
SELECT id, title, views
FROM posts
WHERE status = 'published'
ORDER BY created_at DESC
LIMIT 10;
```

### 什么时候该换掉它

当站点需要多机部署、多写入方时，再考虑 PostgreSQL。
在此之前，YAGNI。
""",
            "SQLite,数据库",
            "published",
            now - timedelta(days=7),
        ),
        (
            "一篇未发布的草稿",
            "这篇草稿只有登录后台才能看到，用于演示草稿与发布的隔离。",
            """## 草稿内容

前台读者看不到这篇文章。

发布流程：后台编辑 → 状态改为 published → 首页出现。
""",
            "草稿",
            "draft",
            now,
        ),
    ]
    for title, summary, content, tags, status, created in samples:
        db.execute(
            "INSERT INTO posts (title, summary, content, tags, status, views,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (title, summary, content, normalize_tags(tags), status,
             created.strftime("%Y-%m-%d %H:%M:%S"),
             created.strftime("%Y-%m-%d %H:%M:%S")),
        )


def init_db():
    """建表 + 种子数据, 应用启动时执行; 重复执行是安全的"""
    fresh = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    try:
        db.executescript(SCHEMA)
        _seed_users(db)
        _seed_posts(db)
        db.commit()
    finally:
        db.close()
    return fresh


# ----------------------------- 文章查询 -----------------------------
def _row_to_dict(row):
    d = dict(row)
    d["tag_list"] = [t for t in d["tags"].strip(",").split(",") if t]
    return d


def list_published(page=1, per_page=10, tag=None):
    """分页返回已发布文章; tag 非空时按标签过滤。返回 (rows, total)"""
    db = get_db()
    where, params = "WHERE status = 'published'", []
    if tag:
        where += " AND tags LIKE ?"
        params.append(f"%,{tag},%")
    total = db.execute(
        f"SELECT COUNT(*) FROM posts {where}", params
    ).fetchone()[0]
    offset = (page - 1) * per_page
    rows = db.execute(
        f"SELECT * FROM posts {where} ORDER BY created_at DESC"
        " LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()
    return [_row_to_dict(r) for r in rows], total


def get_post(post_id, published_only=True):
    """按 id 取文章; published_only=True 时草稿返回 None"""
    db = get_db()
    sql = "SELECT * FROM posts WHERE id = ?"
    if published_only:
        sql += " AND status = 'published'"
    row = db.execute(sql, (post_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_adjacent(post_id):
    """返回 (上一篇, 下一篇), 按发布时间相邻; 均为已发布文章"""
    db = get_db()
    current = db.execute(
        "SELECT created_at FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    if current is None:
        return None, None
    prev = db.execute(
        "SELECT * FROM posts WHERE status = 'published'"
        " AND (created_at < ? OR (created_at = ? AND id < ?))"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (current["created_at"], current["created_at"], post_id),
    ).fetchone()
    nxt = db.execute(
        "SELECT * FROM posts WHERE status = 'published'"
        " AND (created_at > ? OR (created_at = ? AND id > ?))"
        " ORDER BY created_at ASC, id ASC LIMIT 1",
        (current["created_at"], current["created_at"], post_id),
    ).fetchone()
    return (_row_to_dict(prev) if prev else None,
            _row_to_dict(nxt) if nxt else None)


def list_all(page=1, per_page=20):
    """后台用: 不分状态, 按更新时间倒序"""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    offset = (page - 1) * per_page
    rows = db.execute(
        "SELECT * FROM posts ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()
    return [_row_to_dict(r) for r in rows], total


def create_post(title, summary, content, tags, status):
    """新建文章, 返回新 id"""
    db = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = db.execute(
        "INSERT INTO posts (title, summary, content, tags, status, views,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
        (title.strip(), summary.strip(), content, normalize_tags(tags),
         status, now, now),
    )
    db.commit()
    return cur.lastrowid


def update_post(post_id, title, summary, content, tags, status):
    """更新文章"""
    db = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "UPDATE posts SET title = ?, summary = ?, content = ?, tags = ?,"
        " status = ?, updated_at = ? WHERE id = ?",
        (title.strip(), summary.strip(), content, normalize_tags(tags),
         status, now, post_id),
    )
    db.commit()


def delete_post(post_id):
    """删除文章"""
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()


def increment_views(post_id):
    """阅读数 +1"""
    db = get_db()
    db.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
    db.commit()


def get_tag_cloud():
    """返回已发布文章的 [(标签, 次数)], 次数降序"""
    db = get_db()
    rows = db.execute(
        "SELECT tags FROM posts WHERE status = 'published'"
    ).fetchall()
    counter = {}
    for row in rows:
        for tag in [t for t in row["tags"].strip(",").split(",") if t]:
            counter[tag] = counter.get(tag, 0) + 1
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


# ----------------------------- 用户 -----------------------------
def verify_login(username, password):
    """校验管理员账号, 成功返回 True"""
    db = get_db()
    row = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        return False
    return check_password_hash(row["password_hash"], password)
