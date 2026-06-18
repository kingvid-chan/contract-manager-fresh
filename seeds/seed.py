"""Seed demo data — run once after init_db to populate accounts and sample contracts."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.services.auth import hash_password
from app.services.user import get_user_by_username
from app.models.user import User
from app.models.contract import Contract
from app.config import settings


def seed():
    """Create demo accounts and sample contracts if they don't exist."""
    init_db()
    db = SessionLocal()

    try:
        # ── Demo users ──────────────────────────────────────────────────
        if not get_user_by_username(db, settings.demo_admin_username):
            admin = User(
                username=settings.demo_admin_username,
                password_hash=hash_password(settings.demo_admin_password),
                role="admin",
                status="active",
            )
            db.add(admin)
            db.flush()
            print(f"[seed] Created admin user: {settings.demo_admin_username}")

        if not get_user_by_username(db, settings.demo_user_username):
            user = User(
                username=settings.demo_user_username,
                password_hash=hash_password(settings.demo_user_password),
                role="user",
                status="active",
            )
            db.add(user)
            db.flush()
            print(f"[seed] Created regular user: {settings.demo_user_username}")

        db.commit()

        # ── Get admin user for FK ──────────────────────────────────────
        admin_user = get_user_by_username(db, settings.demo_admin_username)
        if not admin_user:
            print("[seed] Admin user not found, skipping contract seeding")
            return

        # ── Sample contracts ────────────────────────────────────────────
        existing = db.query(Contract).count()
        if existing > 0:
            print(f"[seed] {existing} contracts already exist, skipping")
            return

        contracts = [
            {
                "contract_no": "C-20260618-001",
                "title": "软件开发服务合同",
                "party_a": "科技有限公司",
                "party_b": "创新软件工作室",
                "amount": 150000.00,
                "status": "active",
                "remarks": "Web应用开发项目，周期6个月",
            },
            {
                "contract_no": "C-20260618-002",
                "title": "服务器采购合同",
                "party_a": "数据服务中心",
                "party_b": "云端硬件供应商",
                "amount": 85000.00,
                "status": "approved",
                "remarks": "采购10台高性能服务器",
            },
            {
                "contract_no": "C-20260618-003",
                "title": "年度运维服务协议",
                "party_a": "企业信息部",
                "party_b": "运维技术服务公司",
                "amount": 60000.00,
                "status": "draft",
                "remarks": "系统运维与技术支持年度服务",
            },
            {
                "contract_no": "C-20260618-004",
                "title": "市场推广合作协议",
                "party_a": "营销中心",
                "party_b": "数字营销代理公司",
                "amount": 45000.00,
                "status": "expired",
                "remarks": "2025年Q1-Q2线上推广，已到期",
            },
            {
                "contract_no": "C-20260618-005",
                "title": "办公场地租赁合同",
                "party_a": "创业孵化器",
                "party_b": "房地产管理公司",
                "amount": 120000.00,
                "status": "terminated",
                "remarks": "因搬迁提前终止",
            },
        ]

        for cdata in contracts:
            contract = Contract(
                contract_no=cdata["contract_no"],
                title=cdata["title"],
                party_a=cdata["party_a"],
                party_b=cdata["party_b"],
                amount=cdata["amount"],
                status=cdata["status"],
                remarks=cdata["remarks"],
                created_by=admin_user.id,
            )
            db.add(contract)

        db.commit()
        print(f"[seed] Created {len(contracts)} sample contracts")

    except Exception as e:
        db.rollback()
        print(f"[seed] Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("[seed] Done.")
