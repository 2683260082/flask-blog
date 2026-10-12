# -*- coding: utf-8 -*-
"""墨刊 - 启动入口 (业务代码全部在 blog/ 包内)。

启动方式:
    python app.py                 # 开发模式, http://127.0.0.1:5000
    flask --app app run           # 亦可, 导入时已初始化数据库

环境变量 (详见 README):
    BLOG_SECRET_KEY / BLOG_ADMIN_PASSWORD / BLOG_DB / BLOG_SEED_POSTS
"""
import sys

from blog import create_app, render_markdown  # noqa: F401  (render_markdown 供测试引用)

app = create_app()


if __name__ == "__main__":
    # Windows 控制台默认 GBK, 中文打印会乱码, 此处统一为 UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=" * 46)
    print("墨刊已启动: http://127.0.0.1:5000")
    print("后台登录:   http://127.0.0.1:5000/admin/login")
    print("管理员账号: admin / admin123")
    print("=" * 46)
    app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)
