# -*- coding: utf-8 -*-
"""前台蓝图: 首页刊列、文章详情、标签、归档、关于、RSS。"""
from datetime import datetime
from email.utils import format_datetime

from flask import (
    Blueprint, abort, current_app, render_template, request, url_for,
)

import models

bp = Blueprint("front", __name__)


def _page_args():
    """解析页码, 非法值回落到第 1 页"""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    return page


@bp.route("/")
def index():
    page = _page_args()
    per_page = current_app.config["PER_PAGE"]
    rows, total = models.list_published(page=page, per_page=per_page)
    return render_template(
        "index.html", posts=rows, page=page, total=total, per_page=per_page,
        tag_cloud=models.get_tag_cloud(),
    )


@bp.route("/post/<int:post_id>")
def post_detail(post_id):
    post = models.get_post(post_id, published_only=True)
    if post is None:
        abort(404)
    models.increment_views(post_id)
    post["views"] += 1  # 让本页立即显示新计数
    prev_post, next_post = models.get_adjacent(post_id)
    return render_template(
        "post.html", post=post, prev_post=prev_post, next_post=next_post,
    )


@bp.route("/tag/<tag>")
def tag_detail(tag):
    page = _page_args()
    per_page = current_app.config["PER_PAGE"]
    rows, total = models.list_published(page=page, per_page=per_page, tag=tag)
    if total == 0 and page == 1:
        abort(404)  # 标签不存在或下无已发布文章
    return render_template(
        "tag.html", posts=rows, page=page, total=total, per_page=per_page,
        tag=tag, tag_cloud=models.get_tag_cloud(),
    )


@bp.route("/archive")
def archive():
    rows, _ = models.list_published(page=1, per_page=1000)
    # 按年份分组
    groups = {}
    for post in rows:
        year = post["created_at"][:4]
        groups.setdefault(year, []).append(post)
    return render_template("archive.html", groups=groups)


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/feed.xml")
def feed():
    rows, _ = models.list_published(page=1, per_page=20)
    for post in rows:
        post["pub_date"] = format_datetime(
            datetime.strptime(post["created_at"], "%Y-%m-%d %H:%M:%S")
        )
        post["url"] = url_for(
            "front.post_detail", post_id=post["id"], _external=True
        )
    response = render_template(
        "feed.xml",
        posts=rows,
        now_rfc822=format_datetime(datetime.now()),
    )
    return current_app.response_class(
        response, mimetype="application/xml"
    )
