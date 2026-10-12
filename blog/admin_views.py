# -*- coding: utf-8 -*-
"""后台蓝图: 登录、文章管理 (增删改查、草稿/发布)。

所有写操作均要求登录, login_required 只出现在本模块。
"""
from functools import wraps

from flask import (
    Blueprint, abort, flash, redirect, render_template,
    request, session, url_for,
)

from . import models

bp = Blueprint("admin", __name__)

VALID_STATUS = {"draft", "published"}


def login_required(view):
    """未登录访问后台时跳转到登录页"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def _form_values():
    """从表单读取并校验文章字段, 非法则 flash 并返回 None"""
    title = request.form.get("title", "").strip()
    summary = request.form.get("summary", "").strip()
    content = request.form.get("content", "").strip()
    tags = request.form.get("tags", "").strip()
    status = request.form.get("status", "draft")
    if not title:
        flash("标题不能为空", "error")
        return None
    if not content:
        flash("正文不能为空", "error")
        return None
    if status not in VALID_STATUS:
        status = "draft"
    return title, summary, content, tags, status


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("admin.dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if models.verify_login(username, password):
            session["user"] = username
            target = request.args.get("next") or url_for("admin.dashboard")
            if not target.startswith("/"):
                target = url_for("admin.dashboard")
            return redirect(target)
        error = "用户名或密码错误"
    return render_template("admin/login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("front.index"))


@bp.route("/")
@login_required
def dashboard():
    page = request.args.get("page", 1, type=int) or 1
    rows, total = models.list_all(page=max(1, page))
    return render_template(
        "admin/list.html", posts=rows, page=max(1, page),
        total=total, per_page=20,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        values = _form_values()
        if values:
            post_id = models.create_post(*values)
            flash("文章已创建", "ok")
            return redirect(url_for("admin.edit", post_id=post_id))
    return render_template("admin/edit.html", post=None)


@bp.route("/edit/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit(post_id):
    post = models.get_post(post_id, published_only=False)
    if post is None:
        abort(404)
    if request.method == "POST":
        values = _form_values()
        if values:
            models.update_post(post_id, *values)
            flash("文章已保存", "ok")
            return redirect(url_for("admin.edit", post_id=post_id))
    return render_template("admin/edit.html", post=post)


@bp.route("/delete/<int:post_id>", methods=["POST"])
@login_required
def delete(post_id):
    post = models.get_post(post_id, published_only=False)
    if post is None:
        abort(404)
    models.delete_post(post_id)
    flash(f"已删除：{post['title']}", "ok")
    return redirect(url_for("admin.dashboard"))
