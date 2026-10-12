# -*- coding: utf-8 -*-
"""墨刊 - 个人博客应用入口。

启动方式:
    python app.py                 # 开发模式, http://127.0.0.1:5000
    flask --app app run           # 亦可, 导入时已初始化数据库

环境变量:
    BLOG_SECRET_KEY       会话密钥 (生产环境必须设置随机值)
    BLOG_ADMIN_PASSWORD   管理员初始密码 (默认 admin123, 仅首次建库生效)
    BLOG_DB               数据库文件路径 (默认项目根目录 blog.db)
    BLOG_SEED_POSTS       置 0 时不写入演示文章
"""
import os
import sys

import markdown as md_lib
from flask import Flask, render_template
from markupsafe import Markup

import models

# Markdown 渲染器: extra 支持表格/围栏代码, codehilite 负责代码高亮
_MD = md_lib.Markdown(
    extensions=["extra", "codehilite", "toc"],
    extension_configs={
        "codehilite": {"css_class": "highlight", "guess_lang": False},
    },
)


def render_markdown(text):
    """把 Markdown 源码渲染为 HTML (Jinja 过滤器)。

    原生 HTML 按 Markdown 惯例透传——文章仅管理员可写, 属可信输入;
    若未来开放投稿, 需在渲染后增加 HTML 消毒 (如 nh3/bleach)。
    """
    if not text:
        return ""
    _MD.reset()
    return Markup(_MD.convert(text))


def create_app(test_config=None):
    """应用工厂: 配置 → 数据生命周期 → 过滤器 → 蓝图 → 错误页"""
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("BLOG_SECRET_KEY") or "ink-journal-dev-key",
        PER_PAGE=10,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    # 数据库生命周期
    app.teardown_appcontext(models.close_db)

    # 模板过滤器
    app.jinja_env.filters["markdown"] = render_markdown

    # 模板全局量: 页脚年份
    from datetime import datetime
    app.context_processor(lambda: {"now_year": datetime.now().year})

    # 蓝图: 前台 + 后台
    from admin_views import bp as admin_bp
    from views import bp as front_bp
    app.register_blueprint(front_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # 错误页
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    # 建表 + 种子数据 (幂等)
    with app.app_context():
        models.init_db()

    return app


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
