"""Seed 2026 annual quotas for all ICs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sis.db import get_session
from sis.db.models import Quota, User

QUOTAS_2026 = {
    "Nadine Barchecht": 104_750,
    "Omer Snir": 104_750,
    "Stefania Fanari": 104_750,
    "Keiko Navon": 125_700,
    "Nicholas Kirtley": 125_700,
    "Dror Gross": 104_750,
    "Uriel Ross": 104_750,
    "Yos Jacobs": 104_750,
    "Lei Bao": 83_800,
    "Wenze Li": 83_800,
    "ZhenYu Qiao": 83_800,
}

def seed():
    with get_session() as db:
        for name, amount in QUOTAS_2026.items():
            user = db.query(User).filter(User.name == name).first()
            if not user:
                print(f"WARNING: User '{name}' not found, skipping")
                continue
            existing = db.query(Quota).filter(
                Quota.user_id == user.id, Quota.period == "2026"
            ).first()
            if existing:
                existing.amount = amount
                print(f"Updated: {name} -> ${amount:,.0f}")
            else:
                db.add(Quota(user_id=user.id, period="2026", amount=amount))
                print(f"Created: {name} -> ${amount:,.0f}")
        print(f"\nSeeded {len(QUOTAS_2026)} quotas for 2026")

if __name__ == "__main__":
    seed()
