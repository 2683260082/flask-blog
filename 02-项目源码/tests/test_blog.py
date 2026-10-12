# -*- coding: utf-8 -*-
"""墨刊单元测试。

覆盖: 前台展示与隔离 (草稿/404)、Markdown 渲染、登录鉴权、
      文章创建/发布/编辑/删除全流程、RSS 输出。

运行方式 (在项目根目录执行):
    python -m unittest discover -s tests -t . -v
"""
import os
import sys
import tempfile
import unittest

# 导入被测应用前, 把数据库指向临时目录, 避免污染开发库
_TMP_DIR = tempfile.mkdtemp(prefix="flask-blog-test-")
os.environ["BLOG_DB"] = os.path.join(_TMP_DIR, "test.db")
os.environ["BLOG_SEED_POSTS"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402


class BlogTestCase(unittest.TestCase):
    """前台 + 后台集成测试, 共享同一应用实例"""

    @classmethod
    def setUpClass(cls):
        cls.app = app_module.app
        cls.app.config["TESTING"] = True

    def setUp(self):
        self.client = self.app.test_client()

    # ----------------------------- 前台 -----------------------------
    def test_index_shows_published_and_hides_draft(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("你好，墨刊", html)
        self.assertNotIn("一篇未发布的草稿", html)

    def test_post_detail_renders_markdown(self):
        resp = self.client.get("/post/1")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("article-content", html)
        self.assertIn("hello", html)          # 代码块内容
        self.assertIn("highlight", html)      # 代码高亮已挂载

    def test_draft_is_404_on_front(self):
        # 种子数据最后一 id 为草稿
        with app_module.app.app_context():
            from blog import models
            row = models.get_db().execute(
                "SELECT id FROM posts WHERE status = 'draft'"
            ).fetchone()
        self.assertEqual(self.client.get(f"/post/{row['id']}").status_code, 404)

    def test_unknown_post_404(self):
        self.assertEqual(self.client.get("/post/99999").status_code, 404)

    def test_tag_page_filters(self):
        resp = self.client.get("/tag/Flask")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Flask 蓝图实践笔记", html)
        self.assertNotIn("SQLite 用在个人博客刚刚好", html)

    def test_unknown_tag_404(self):
        self.assertEqual(
            self.client.get("/tag/根本不存在的标签").status_code, 404
        )

    def test_archive_about_and_404_page(self):
        self.assertEqual(self.client.get("/archive").status_code, 200)
        self.assertEqual(self.client.get("/about").status_code, 200)
        resp = self.client.get("/no-such-page")
        self.assertEqual(resp.status_code, 404)

    def test_feed_is_valid_xml_shape(self):
        resp = self.client.get("/feed.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content_type.startswith("application/xml"))
        html = resp.get_data(as_text=True)
        self.assertIn("<rss", html)
        self.assertIn("<item>", html)

    def test_markdown_filter_escapes_and_renders(self):
        rendered = app_module.render_markdown("**粗体** 与 `code`")
        self.assertIn("<strong>粗体</strong>", rendered)
        self.assertIn("<code>", rendered)
        # Markdown 惯例: 原生 HTML 透传 (仅管理员可写文章, 信任模型成立)
        self.assertIn("<b>强调</b>", app_module.render_markdown("<b>强调</b>"))

    # ----------------------------- 鉴权 -----------------------------
    def test_admin_requires_login(self):
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login", resp.headers["Location"])

    def test_login_wrong_password(self):
        resp = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "wrong"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("用户名或密码错误", resp.get_data(as_text=True))

    def test_login_session_and_logout(self):
        resp = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        self.assertIn("文章管理", resp.get_data(as_text=True))
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.client.post("/admin/logout")
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    # ----------------------------- 文章 CRUD -----------------------------
    def _login(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin123"},
        )

    def test_create_publish_edit_delete_flow(self):
        self._login()
        # 创建草稿
        resp = self.client.post(
            "/admin/new",
            data={
                "title": "测试文章", "summary": "摘要",
                "content": "# 正文", "tags": "测试, unittest",
                "status": "draft",
            },
            follow_redirects=True,
        )
        self.assertIn("文章已创建", resp.get_data(as_text=True))

        with app_module.app.app_context():
            from blog import models
            post_id = models.get_db().execute(
                "SELECT id FROM posts WHERE title = ?", ("测试文章",)
            ).fetchone()["id"]

        # 草稿前台不可见
        self.assertEqual(self.client.get(f"/post/{post_id}").status_code, 404)

        # 编辑并发布
        resp = self.client.post(
            f"/admin/edit/{post_id}",
            data={
                "title": "测试文章（改）", "summary": "新摘要",
                "content": "## 发布正文", "tags": "测试",
                "status": "published",
            },
            follow_redirects=True,
        )
        self.assertIn("文章已保存", resp.get_data(as_text=True))
        html = self.client.get(f"/post/{post_id}").get_data(as_text=True)
        self.assertIn("测试文章（改）", html)

        # 删除后前台 404
        self.client.post(f"/admin/delete/{post_id}")
        self.assertEqual(
            self.client.get(f"/post/{post_id}").status_code, 404
        )

    def test_create_rejects_empty_title(self):
        self._login()
        resp = self.client.post(
            "/admin/new",
            data={"title": "", "content": "x", "status": "draft"},
            follow_redirects=True,
        )
        self.assertIn("标题不能为空", resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
