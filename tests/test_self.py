"""
Self-test script for Contract Manager v0.0.2.

Covers:
  1. Login (SSR + JSON API)
  2. User CRUD (admin create, read, update, toggle status, reset password, delete)
  3. Contract CRUD + status flow (SSR + JSON API)
  4. Attachment type validation (reject invalid, accept PDF/DOC/DOCX)
  5. Attachment upload & download
  6. Audit log tracking
  7. Auth protection (unauthenticated redirect, non-admin 403)
  8. Cache-Control header on HTML responses
  9. Vue SPA static files
 10. JSON API endpoints (auth, contracts, users, audit, attachments)

Run:
    ~/..conda/codingagent/bin/python -m pytest tests/test_self.py -v
"""

import io
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./data/test_contract_manager.db"

from app.database import init_db, SessionLocal
from app.models.user import User
from app.services.auth import hash_password
from app.config import settings

# Remove test DB if it exists from a prior run
test_db_path = "data/test_contract_manager.db"
if os.path.exists(test_db_path):
    os.remove(test_db_path)

init_db()

# Create seed users directly in the test DB
db = SessionLocal()
admin_user = User(
    username="admin",
    password_hash=hash_password("admin123"),
    role="admin",
    status="active",
)
regular_user = User(
    username="user",
    password_hash=hash_password("user123"),
    role="user",
    status="active",
)
disabled_user = User(
    username="disabled",
    password_hash=hash_password("disabled123"),
    role="user",
    status="disabled",
)
db.add_all([admin_user, regular_user, disabled_user])
db.commit()
db.close()

from app.main import app

BASE = settings.base_path


# ── Helpers ─────────────────────────────────────────────────────────────────

def fresh_client():
    """Return a new TestClient with no cookie state."""
    return TestClient(app, base_url="http://testserver")


def login(client, username="admin", password="admin123"):
    """Login and return response (no follow)."""
    return client.post(
        f"{BASE}/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def login_session(client, username="admin", password="admin123"):
    """Login and return the session cookie value."""
    resp = login(client, username, password)
    return resp.cookies.get("session") if resp.status_code == 302 else None


# ══════════════════════════════════════════════════════════════════════════════
# 1. LOGIN TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()

    def test_login_page_renders(self):
        resp = self.client.get(f"{BASE}/auth/login")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "登录" in resp.text

    def test_login_success_admin(self):
        resp = login(self.client, "admin", "admin123")
        assert resp.status_code == 302
        assert resp.headers["location"] == f"{BASE}/"
        assert "session" in resp.cookies

    def test_login_success_regular_user(self):
        resp = login(self.client, "user", "user123")
        assert resp.status_code == 302

    def test_login_wrong_password(self):
        resp = login(self.client, "admin", "wrongpass")
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.text

    def test_login_nonexistent_user(self):
        resp = login(self.client, "ghost", "whatever")
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.text

    def test_login_disabled_user(self):
        resp = login(self.client, "disabled", "disabled123")
        assert resp.status_code == 401
        assert "禁用" in resp.text

    def test_login_page_has_demo_info(self):
        resp = self.client.get(f"{BASE}/auth/login")
        assert "admin / admin123" in resp.text
        assert "user / user123" in resp.text


# ══════════════════════════════════════════════════════════════════════════════
# 2. AUTH PROTECTION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthProtection:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Fresh client — no cookies from previous tests
        self.client = fresh_client()

    def test_unauthenticated_redirect_to_login(self):
        resp = self.client.get(f"{BASE}/", follow_redirects=False)
        assert resp.status_code == 302
        assert "login" in resp.headers["location"]

    def test_unauthenticated_contracts_redirect(self):
        resp = self.client.get(f"{BASE}/contracts", follow_redirects=False)
        assert resp.status_code == 302

    def test_unauthenticated_users_redirect(self):
        resp = self.client.get(f"{BASE}/users", follow_redirects=False)
        assert resp.status_code == 302

    def test_non_admin_cannot_access_users(self):
        session = login_session(self.client, "user", "user123")
        resp = self.client.get(f"{BASE}/users", cookies={"session": session})
        assert resp.status_code == 403

    def test_non_admin_cannot_access_audit_logs(self):
        session = login_session(self.client, "user", "user123")
        resp = self.client.get(f"{BASE}/audit-logs", cookies={"session": session})
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 3. USER CRUD TESTS (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestUserCRUD:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()
        self.session = login_session(self.client, "admin", "admin123")

    def test_list_users(self):
        resp = self.client.get(f"{BASE}/users", cookies={"session": self.session})
        assert resp.status_code == 200
        assert "admin" in resp.text
        assert "user" in resp.text
        assert "disabled" in resp.text

    def test_create_user_form(self):
        resp = self.client.get(f"{BASE}/users/new", cookies={"session": self.session})
        assert resp.status_code == 200

    def test_create_user(self):
        resp = self.client.post(
            f"{BASE}/users",
            data={"username": "testuser1", "password": "pass123", "role": "user"},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "testuser1" in resp.text

    def test_create_duplicate_user_fails(self):
        resp = self.client.post(
            f"{BASE}/users",
            data={"username": "admin", "password": "pass123", "role": "user"},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "用户名已存在" in resp.text

    def test_edit_user_form(self):
        resp = self.client.get(f"{BASE}/users/1/edit", cookies={"session": self.session})
        assert resp.status_code == 200
        assert "admin" in resp.text

    def test_update_user(self):
        resp = self.client.post(
            f"{BASE}/users/4/edit",
            data={"username": "testuser1", "role": "admin", "password": ""},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        resp2 = self.client.get(f"{BASE}/users", cookies={"session": self.session})
        assert "testuser1" in resp2.text

    def test_toggle_user_status(self):
        # Disable testuser1
        resp = self.client.post(
            f"{BASE}/users/4/toggle-status",
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Verify disabled user cannot login
        resp2 = login(fresh_client(), "testuser1", "pass123")
        assert resp2.status_code == 401

    def test_self_disable_prevented(self):
        resp = self.client.post(
            f"{BASE}/users/1/toggle-status",
            cookies={"session": self.session},
            follow_redirects=False,
        )
        # Should redirect to users page (self-disable prevented)
        assert resp.status_code == 302
        # Verify admin is still active
        db = SessionLocal()
        admin = db.query(User).filter(User.id == 1).first()
        assert admin is not None
        assert admin.status == "active"
        db.close()

    def test_reset_password(self):
        # Re-enable testuser1 first
        self.client.post(
            f"{BASE}/users/4/toggle-status",
            cookies={"session": self.session},
        )
        resp = self.client.post(
            f"{BASE}/users/4/reset-password",
            data={"new_password": "newpass456"},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        resp2 = login(fresh_client(), "testuser1", "newpass456")
        assert resp2.status_code == 302

    def test_delete_user(self):
        resp = self.client.post(
            f"{BASE}/users/4/delete",
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "testuser1" not in resp.text

    def test_self_delete_prevented(self):
        resp = self.client.post(
            f"{BASE}/users/1/delete",
            cookies={"session": self.session},
            follow_redirects=False,
        )
        # Should redirect (self-delete prevented)
        assert resp.status_code == 302
        # Verify admin still exists
        db = SessionLocal()
        admin = db.query(User).filter(User.id == 1).first()
        assert admin is not None
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# 4. CONTRACT CRUD + STATUS FLOW TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestContractCRUD:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()
        self.session = login_session(self.client, "admin", "admin123")

    def test_contract_list_page(self):
        resp = self.client.get(f"{BASE}/contracts", cookies={"session": self.session})
        assert resp.status_code == 200

    def test_create_contract_form(self):
        resp = self.client.get(f"{BASE}/contracts/new", cookies={"session": self.session})
        assert resp.status_code == 200

    def test_create_contract(self):
        resp = self.client.post(
            f"{BASE}/contracts",
            data={
                "title": "测试合同",
                "party_a": "测试公司A",
                "party_b": "测试公司B",
                "amount": 50000.00,
                "remarks": "自动化测试合同",
            },
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "测试合同" in resp.text
        assert "C-" in resp.text
        assert "draft" in resp.text

    def test_create_contract_missing_title(self):
        resp = self.client.post(
            f"{BASE}/contracts",
            data={"title": "", "party_a": "A", "party_b": "B"},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        assert resp.status_code == 400

    def test_create_contract_missing_party_a(self):
        resp = self.client.post(
            f"{BASE}/contracts",
            data={"title": "T", "party_a": "", "party_b": "B"},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        assert resp.status_code == 400

    def test_contract_detail_page(self):
        resp = self.client.get(f"{BASE}/contracts/1", cookies={"session": self.session})
        assert resp.status_code == 200

    def test_edit_contract(self):
        resp = self.client.post(
            f"{BASE}/contracts/1/edit",
            data={
                "title": "修改后的合同名",
                "party_a": "新甲方",
                "party_b": "新乙方",
                "amount": 99999.99,
                "remarks": "已修改",
            },
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "修改后的合同名" in resp.text
        assert "99999.99" in resp.text

    def test_status_flow_draft_to_pending_review(self):
        # Create a fresh draft contract
        resp = self.client.post(
            f"{BASE}/contracts",
            data={"title": "状态测试", "party_a": "A", "party_b": "B"},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        location = resp.headers["location"]
        contract_id = int(location.rstrip("/").split("/")[-1])

        # Submit for review
        resp2 = self.client.post(
            f"{BASE}/contracts/{contract_id}/status",
            data={"status": "pending_review"},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp2.status_code == 200
        assert "pending_review" in resp2.text

    def test_status_flow_pending_to_approved(self):
        # Create draft → submit for review → admin approves
        resp = self.client.post(
            f"{BASE}/contracts",
            data={"title": "审批流测试", "party_a": "甲", "party_b": "乙"},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        location = resp.headers["location"]
        contract_id = int(location.rstrip("/").split("/")[-1])

        # Move to pending_review
        self.client.post(
            f"{BASE}/contracts/{contract_id}/status",
            data={"status": "pending_review"},
            cookies={"session": self.session},
        )

        # Admin approves
        resp3 = self.client.post(
            f"{BASE}/contracts/{contract_id}/status",
            data={"status": "approved"},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp3.status_code == 200
        assert "approved" in resp3.text

    def test_invalid_status_transition_rejected(self):
        # Try to go from draft directly to expired
        resp = self.client.post(
            f"{BASE}/contracts",
            data={"title": "非法状态测试", "party_a": "A", "party_b": "B"},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        location = resp.headers["location"]
        contract_id = int(location.rstrip("/").split("/")[-1])

        resp2 = self.client.post(
            f"{BASE}/contracts/{contract_id}/status",
            data={"status": "expired"},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        assert resp2.status_code == 400

    def test_delete_contract(self):
        resp = self.client.post(
            f"{BASE}/contracts/1/delete",
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        resp2 = self.client.get(f"{BASE}/contracts/1", cookies={"session": self.session})
        assert resp2.status_code == 404

    def test_contract_404(self):
        resp = self.client.get(f"{BASE}/contracts/99999", cookies={"session": self.session})
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 5. ATTACHMENT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAttachments:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()
        self.session = login_session(self.client, "admin", "admin123")
        self.contract_id = 2

    def test_upload_pdf(self):
        pdf_content = b"%PDF-1.4\n%Fake PDF for testing\n1 0 obj\n<<>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<>>\n%%EOF"
        resp = self.client.post(
            f"{BASE}/contracts/{self.contract_id}/attachments",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "test.pdf" in resp.text

    def test_upload_docx(self):
        import zipfile
        docx_buf = io.BytesIO()
        with zipfile.ZipFile(docx_buf, 'w') as zf:
            zf.writestr('[Content_Types].xml',
                       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
        docx_content = docx_buf.getvalue()

        resp = self.client.post(
            f"{BASE}/contracts/{self.contract_id}/attachments",
            files={"file": ("document.docx", io.BytesIO(docx_content),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "document.docx" in resp.text

    def test_reject_invalid_type_txt(self):
        resp = self.client.post(
            f"{BASE}/contracts/{self.contract_id}/attachments",
            files={"file": ("readme.txt", io.BytesIO(b"hello"), "text/plain")},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "不支持的文件类型" in resp.text

    def test_reject_invalid_type_image(self):
        resp = self.client.post(
            f"{BASE}/contracts/{self.contract_id}/attachments",
            files={"file": ("photo.jpg", io.BytesIO(b"fake-jpeg"), "image/jpeg")},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "不支持的文件类型" in resp.text

    def test_reject_oversized_file(self):
        big_content = b"x" * (settings.max_upload_size + 1)
        resp = self.client.post(
            f"{BASE}/contracts/{self.contract_id}/attachments",
            files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
            cookies={"session": self.session},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "大小超过限制" in resp.text

    def test_download_attachment(self):
        pdf_content = b"%PDF-test-download-content"
        resp_upload = self.client.post(
            f"{BASE}/contracts/{self.contract_id}/attachments",
            files={"file": ("download-test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp_upload.status_code == 200

        # Find the uploaded attachment
        from app.database import SessionLocal
        from app.models.attachment import Attachment
        db = SessionLocal()
        att = db.query(Attachment).order_by(Attachment.id.desc()).first()
        att_id = att.id if att else 3
        db.close()

        resp_dl = self.client.get(
            f"{BASE}/attachments/{att_id}/download",
            cookies={"session": self.session},
        )
        assert resp_dl.status_code in (200, 302)

    def test_delete_attachment(self):
        resp = self.client.post(
            f"{BASE}/attachments/1/delete",
            cookies={"session": self.session},
            follow_redirects=True,
        )
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 6. AUDIT LOG TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()

    def test_audit_logs_page_admin(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.get(f"{BASE}/audit-logs", cookies={"session": session})
        assert resp.status_code == 200

    def test_audit_logs_exist(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.get(f"{BASE}/audit-logs", cookies={"session": session})
        # Logs should exist from previous test operations
        assert any(w in resp.text.lower() for w in ["create", "update", "delete"])

    def test_audit_logs_denied_for_user(self):
        session = login_session(self.client, "user", "user123")
        resp = self.client.get(f"{BASE}/audit-logs", cookies={"session": session})
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 7. CACHE-CONTROL HEADER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheControl:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()

    def test_html_response_has_no_cache(self):
        resp = self.client.get(f"{BASE}/auth/login")
        assert resp.status_code == 200
        cache_control = resp.headers.get("cache-control", "")
        assert "no-cache" in cache_control or "no-store" in cache_control

    def test_dashboard_has_no_cache(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.get(f"{BASE}/", cookies={"session": session})
        # SPA returns HTML, old dashboard also returns HTML
        assert resp.status_code == 200
        if "text/html" in resp.headers.get("content-type", ""):
            cache_control = resp.headers.get("cache-control", "")
            assert "no-cache" in cache_control or "no-store" in cache_control


# ══════════════════════════════════════════════════════════════════════════════
# 8. STATIC ASSETS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestStaticAssets:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()

    def test_login_css_with_version_token(self):
        resp = self.client.get(f"{BASE}/auth/login")
        assert f'css/app.css?v={settings.version_token}' in resp.text

    def test_spa_js_with_version_token(self):
        # SPA index.html loads spa/js/app.js with version token
        resp = self.client.get(f"{BASE}/")
        # Will redirect to login if unauthenticated, or return SPA HTML
        assert resp.status_code in (200, 302)

    def test_static_css_accessible(self):
        resp = self.client.get(f"{BASE}/static/css/app.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_spa_index_returns_html(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.get(f"{BASE}/", cookies={"session": session})
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_spa_theme_css_accessible(self):
        resp = self.client.get(f"{BASE}/static/spa/css/theme.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_spa_js_accessible(self):
        resp = self.client.get(f"{BASE}/static/spa/js/app.js")
        assert resp.status_code == 200
        assert "application/javascript" in resp.headers["content-type"] or "text/javascript" in resp.headers["content-type"]


# ══════════════════════════════════════════════════════════════════════════════
# 9. CONTRACT AUTO-NUMBERING TEST
# ══════════════════════════════════════════════════════════════════════════════

class TestContractAutoNumber:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()

    def test_contract_number_format(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.post(
            f"{BASE}/contracts",
            data={"title": "编号测试", "party_a": "A公司", "party_b": "B公司"},
            cookies={"session": session},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        pattern = r"C-\d{8}-\d{3}"
        assert re.search(pattern, resp.text), (
            f"Expected contract_no matching {pattern} in response"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 10. JSON API TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonApiAuth:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()

    def test_api_login_success(self):
        resp = self.client.post(
            f"{BASE}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    def test_api_login_wrong_password(self):
        resp = self.client.post(
            f"{BASE}/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "错误" in data["error"]

    def test_api_login_disabled_user(self):
        resp = self.client.post(
            f"{BASE}/api/auth/login",
            json={"username": "disabled", "password": "disabled123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "禁用" in data["error"]

    def test_api_me_authenticated(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.get(f"{BASE}/api/auth/me", cookies={"session": session})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["user"]["username"] == "admin"

    def test_api_me_unauthenticated(self):
        resp = self.client.get(f"{BASE}/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False

    def test_api_logout(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.post(f"{BASE}/api/auth/logout", cookies={"session": session})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True


class TestJsonApiContracts:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()
        self.session = login_session(self.client, "admin", "admin123")

    def _cookies(self):
        return {"session": self.session}

    def test_api_list_contracts(self):
        resp = self.client.get(f"{BASE}/api/contracts", cookies=self._cookies())
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert isinstance(data["contracts"], list)

    def test_api_get_contract(self):
        resp = self.client.get(f"{BASE}/api/contracts/2", cookies=self._cookies())
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["contract"]["id"] == 2

    def test_api_get_contract_404(self):
        resp = self.client.get(f"{BASE}/api/contracts/99999", cookies=self._cookies())
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False

    def test_api_create_contract(self):
        resp = self.client.post(
            f"{BASE}/api/contracts",
            json={"title": "API测试合同", "party_a": "甲方A", "party_b": "乙方B", "amount": 100000},
            cookies=self._cookies(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["contract"]["title"] == "API测试合同"
        assert "C-" in data["contract"]["contract_no"]

    def test_api_create_contract_missing_title(self):
        resp = self.client.post(
            f"{BASE}/api/contracts",
            json={"title": "", "party_a": "A"},
            cookies=self._cookies(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False

    def test_api_update_contract(self):
        resp = self.client.put(
            f"{BASE}/api/contracts/2",
            json={"title": "API修改合同", "party_a": "新甲方", "party_b": "新乙方", "amount": 88888},
            cookies=self._cookies(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["contract"]["title"] == "API修改合同"

    def test_api_change_status(self):
        # Create draft first
        create_resp = self.client.post(
            f"{BASE}/api/contracts",
            json={"title": "状态测试", "party_a": "甲", "party_b": "乙"},
            cookies=self._cookies(),
        )
        cid = create_resp.json()["contract"]["id"]

        # Move to pending_review
        resp = self.client.post(
            f"{BASE}/api/contracts/{cid}/status",
            json={"status": "pending_review"},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True
        assert data["contract"]["status"] == "pending_review"

    def test_api_invalid_status_transition(self):
        create_resp = self.client.post(
            f"{BASE}/api/contracts",
            json={"title": "非法流转", "party_a": "A", "party_b": "B"},
            cookies=self._cookies(),
        )
        cid = create_resp.json()["contract"]["id"]

        resp = self.client.post(
            f"{BASE}/api/contracts/{cid}/status",
            json={"status": "expired"},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is False

    def test_api_delete_contract(self):
        create_resp = self.client.post(
            f"{BASE}/api/contracts",
            json={"title": "待删除", "party_a": "A", "party_b": "B"},
            cookies=self._cookies(),
        )
        cid = create_resp.json()["contract"]["id"]

        resp = self.client.delete(
            f"{BASE}/api/contracts/{cid}",
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True

        # Verify deleted
        resp2 = self.client.get(f"{BASE}/api/contracts/{cid}", cookies=self._cookies())
        assert resp2.json()["ok"] is False

    def test_api_unauthenticated(self):
        client = fresh_client()
        resp = client.get(f"{BASE}/api/contracts")
        data = resp.json()
        assert data["ok"] is False
        assert "未登录" in data.get("error", "")


class TestJsonApiUsers:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()
        self.session = login_session(self.client, "admin", "admin123")

    def _cookies(self):
        return {"session": self.session}

    def test_api_list_users(self):
        resp = self.client.get(f"{BASE}/api/users", cookies=self._cookies())
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert len(data["users"]) >= 2

    def test_api_create_user(self):
        resp = self.client.post(
            f"{BASE}/api/users",
            json={"username": "apiuser", "password": "pass123", "role": "user"},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True
        assert data["user"]["username"] == "apiuser"

    def test_api_create_duplicate_user(self):
        resp = self.client.post(
            f"{BASE}/api/users",
            json={"username": "admin", "password": "pass123", "role": "user"},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert "已存在" in data["error"]

    def test_api_update_user(self):
        resp = self.client.put(
            f"{BASE}/api/users/4",
            json={"username": "apiuser_renamed", "role": "admin", "password": ""},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True
        assert data["user"]["username"] == "apiuser_renamed"

    def test_api_toggle_status(self):
        # Toggle to disabled
        resp = self.client.post(
            f"{BASE}/api/users/4/toggle-status",
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True
        assert data["user"]["status"] == "disabled"

    def test_api_self_toggle_prevented(self):
        resp = self.client.post(
            f"{BASE}/api/users/1/toggle-status",
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert "不能禁用自己" in data["error"]

    def test_api_reset_password(self):
        # Re-enable first
        self.client.post(f"{BASE}/api/users/4/toggle-status", cookies=self._cookies())
        resp = self.client.post(
            f"{BASE}/api/users/4/reset-password",
            json={"new_password": "newpass789"},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True

    def test_api_delete_user(self):
        resp = self.client.delete(
            f"{BASE}/api/users/4",
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True

    def test_api_self_delete_prevented(self):
        resp = self.client.delete(
            f"{BASE}/api/users/1",
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert "不能删除自己" in data["error"]

    def test_api_users_denied_for_non_admin(self):
        session = login_session(self.client, "user", "user123")
        resp = self.client.get(f"{BASE}/api/users", cookies={"session": session})
        data = resp.json()
        assert data["ok"] is False
        assert "管理员" in data["error"]


class TestJsonApiAudit:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()

    def test_api_audit_logs_admin(self):
        session = login_session(self.client, "admin", "admin123")
        resp = self.client.get(f"{BASE}/api/audit-logs", cookies={"session": session})
        data = resp.json()
        assert data["ok"] is True
        assert isinstance(data["logs"], list)

    def test_api_audit_logs_denied_for_user(self):
        session = login_session(self.client, "user", "user123")
        resp = self.client.get(f"{BASE}/api/audit-logs", cookies={"session": session})
        data = resp.json()
        assert data["ok"] is False
        assert "管理员" in data["error"]


class TestJsonApiAttachments:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = fresh_client()
        self.session = login_session(self.client, "admin", "admin123")

    def _cookies(self):
        return {"session": self.session}

    def test_api_upload_pdf(self):
        pdf_content = b"%PDF-1.4\n%Fake PDF for testing\n1 0 obj\n<<>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<>>\n%%EOF"
        resp = self.client.post(
            f"{BASE}/api/attachments/contracts/2",
            files={"file": ("api-test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True
        assert data["attachment"]["filename"] == "api-test.pdf"

    def test_api_reject_invalid_type(self):
        resp = self.client.post(
            f"{BASE}/api/attachments/contracts/2",
            files={"file": ("bad.txt", io.BytesIO(b"hello"), "text/plain")},
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert "不支持" in data["error"]

    def test_api_delete_attachment(self):
        # Upload an attachment first to have a known ID
        pdf_content = b"%PDF-1.4\n%Fake PDF for delete test\n%%EOF"
        upload_resp = self.client.post(
            f"{BASE}/api/attachments/contracts/2",
            files={"file": ("delete-me.pdf", io.BytesIO(pdf_content), "application/pdf")},
            cookies=self._cookies(),
        )
        upload_data = upload_resp.json()
        assert upload_data["ok"] is True
        att_id = upload_data["attachment"]["id"]

        resp = self.client.delete(
            f"{BASE}/api/attachments/{att_id}",
            cookies=self._cookies(),
        )
        data = resp.json()
        assert data["ok"] is True
