# -*- coding: utf-8 -*-
"""墨刊应用包。

包内分工:
    __init__.py     应用工厂、Markdown 过滤器、蓝图装配
    models.py       数据访问层 (建表、种子、文章 CRUD)
    views.py        前台蓝图 (首页/详情/标签/归档/RSS)
    admin_views.py  后台蓝图 (登录、文章管理, 全部要求鉴权)
    templates/      页面模板
    static/         样式与静态资源
"""
import os
from datetime import datetime

import markdown as md_lib
from flask import Flask, render_template
from markupsafe import Markup

from . import models

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
    app = Flask(__name__)  # __name__="blog" → 模板/静态资源定位于包内
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

    # 模板过滤器与全局量
    app.jinja_env.filters["markdown"] = render_markdown
    app.context_processor(lambda: {"now_year": datetime.now().year})

    # 蓝图: 前台 + 后台
    from .admin_views import bp as admin_bp
    from .views import bp as front_bp
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
