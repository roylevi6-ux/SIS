"""Seed the real org hierarchy + backfill accounts.owner_id.

Run: python -m scripts.migrate_hierarchy

Idempotent -- safe to run multiple times (get_or_create pattern).
"""

from __future__ import annotations
import logging
from sis.db.session import get_session
from sis.db.models import Base, User, Team, Account
from sis.db.engine import get_engine

logger = logging.getLogger(__name__)


def _get_or_create_user(session, *, name, email, role, team_id=None):
    user = session.query(User).filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, role=role, team_id=team_id)
        session.add(user)
        session.flush()
        logger.info("Created user: %s (%s)", name, role)
    return user


def _get_or_create_team(session, *, name, level, parent_id=None):
    team = session.query(Team).filter_by(name=name).first()
    if not team:
        team = Team(name=name, level=level, parent_id=parent_id)
        session.add(team)
        session.flush()
        logger.info("Created team: %s (%s)", name, level)
    return team


def seed_org_tree():
    """Create the full org hierarchy."""
    # Ensure tables exist
    Base.metadata.create_all(get_engine())

    with get_session() as s:
        # -- Root org --
        root = _get_or_create_team(s, name="Sales Org", level="org")

        # -- GM --
        aviram = _get_or_create_user(s, name="Aviram Ganor", email="aviram.ganor@riskified.com", role="gm")
        root.leader_id = aviram.id

        # -- VP: Gili --
        div_gili = _get_or_create_team(s, name="Gili Gertzberg Division", level="division", parent_id=root.id)
        gili = _get_or_create_user(s, name="Gili Gertzberg", email="gili.gertzberg@riskified.com", role="vp", team_id=div_gili.id)
        div_gili.leader_id = gili.id

        #   TL: Bar Barda
        team_bar = _get_or_create_team(s, name="Bar Barda Team", level="team", parent_id=div_gili.id)
        bar = _get_or_create_user(s, name="Bar Barda", email="bar.barda@riskified.com", role="team_lead", team_id=team_bar.id)
        team_bar.leader_id = bar.id
        _get_or_create_user(s, name="Dror Peter Gross", email="dror.gross@riskified.com", role="ic", team_id=team_bar.id)
        _get_or_create_user(s, name="Uriel Ross", email="uriel.ross@riskified.com", role="ic", team_id=team_bar.id)
        _get_or_create_user(s, name="Yos Jacobs", email="yos.jacobs@riskified.com", role="ic", team_id=team_bar.id)

        #   TL: Ying Wang
        team_ying = _get_or_create_team(s, name="Ying Wang Team", level="team", parent_id=div_gili.id)
        ying = _get_or_create_user(s, name="Ying Wang", email="ying.wang@riskified.com", role="team_lead", team_id=team_ying.id)
        team_ying.leader_id = ying.id
        _get_or_create_user(s, name="Lei Bao", email="lei.bao@riskified.com", role="ic", team_id=team_ying.id)
        _get_or_create_user(s, name="ZhenYu Qiao", email="zhenyu.qiao@riskified.com", role="ic", team_id=team_ying.id)
        _get_or_create_user(s, name="Wenze Li", email="wenze.li@riskified.com", role="ic", team_id=team_ying.id)

        # -- VP: Roy (also Admin) --
        div_roy = _get_or_create_team(s, name="Roy Levi Erez Division", level="division", parent_id=root.id)
        roy = _get_or_create_user(s, name="Roy Levi Erez", email="roy.levierez@riskified.com", role="admin", team_id=div_roy.id)
        div_roy.leader_id = roy.id

        #   TL: Lachlan Taylor
        team_lachlan = _get_or_create_team(s, name="Lachlan Taylor Team", level="team", parent_id=div_roy.id)
        lachlan = _get_or_create_user(s, name="Lachlan Taylor", email="lachlan.taylor@riskified.com", role="team_lead", team_id=team_lachlan.id)
        team_lachlan.leader_id = lachlan.id
        _get_or_create_user(s, name="David Nathan Chester", email="david.chester@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Lonnie Lee", email="lonnie.lee@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Takuya Hasegawa", email="takuya.hasegawa@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Keiko Navon", email="keiko.navon@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Nicholas Kirtley", email="nicholas.kirtley@riskified.com", role="ic", team_id=team_lachlan.id)

        #   TL: Lisa Lachkar
        team_lisa = _get_or_create_team(s, name="Lisa Lachkar Team", level="team", parent_id=div_roy.id)
        lisa = _get_or_create_user(s, name="Lisa Lachkar", email="lisa.lachkar@riskified.com", role="team_lead", team_id=team_lisa.id)
        team_lisa.leader_id = lisa.id
        _get_or_create_user(s, name="Nadine Barchechath", email="nadine.barchechath@riskified.com", role="ic", team_id=team_lisa.id)
        _get_or_create_user(s, name="Stefania Fanari", email="stefania.fanari@riskified.com", role="ic", team_id=team_lisa.id)
        _get_or_create_user(s, name="Omer Snir", email="omer.snir@riskified.com", role="ic", team_id=team_lisa.id)

        s.flush()
        logger.info("Org tree seeded: %d users, %d teams",
                     s.query(User).count(), s.query(Team).count())


def backfill_owner_ids():
    """Match existing accounts.ae_owner to User records and set owner_id."""
    with get_session() as s:
        accounts = s.query(Account).filter(Account.owner_id.is_(None)).all()
        matched = 0
        for acct in accounts:
            if not acct.ae_owner:
                continue
            # Try exact match first, then partial (first name) match
            user = s.query(User).filter(User.name == acct.ae_owner).first()
            if not user:
                user = s.query(User).filter(User.name.ilike(acct.ae_owner + "%")).first()
            if user:
                acct.owner_id = user.id
                matched += 1
        s.flush()
        logger.info("Backfilled owner_id on %d / %d accounts", matched, len(accounts))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_org_tree()
    backfill_owner_ids()
    print("Migration complete.")
