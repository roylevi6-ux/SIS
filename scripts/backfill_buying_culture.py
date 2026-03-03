"""One-shot backfill: set buying_culture for existing accounts.

Usage:
    .venv/bin/python -m scripts.backfill_buying_culture

Lists all accounts and their current buying_culture.
To update specific accounts to proxy_delegated, add them to PROXY_DELEGATED_ACCOUNTS.
"""
from sis.db.session import get_session
from sis.db.models import Account

# Mapping: account_name (case-insensitive) -> buying_culture
# Default is "direct" — only list proxy_delegated accounts here
PROXY_DELEGATED_ACCOUNTS: list[str] = [
    "ANA_X",
    "Adastria_Co___Ltd_",
    "BASE__Inc_",
    "JTB",
    "Japan_Airlines",
    "Mont_bell_Co___Ltd_",
    "Poke_mon_Center",
    "Rakuten_Ichiba",
    "Tokyo_Disney_Resort_Oriental_Land_",
    "VELTRA_Corporation",
    "monotaro",
    "nintendo",
    "zaiko",
]


def main():
    proxy_set = {name.lower() for name in PROXY_DELEGATED_ACCOUNTS}
    with get_session() as session:
        accounts = session.query(Account).order_by(Account.account_name).all()
        updated = 0
        print(f"\n{'Account':<30} {'Current':<15} {'Action'}")
        print("-" * 60)
        for account in accounts:
            if account.account_name.lower() in proxy_set:
                account.buying_culture = "proxy_delegated"
                updated += 1
                print(f"  {account.account_name:<28} {account.buying_culture:<15} → proxy_delegated")
            else:
                print(f"  {account.account_name:<28} {account.buying_culture:<15} (unchanged)")
        session.commit()
        print(f"\nDone. Updated {updated} accounts to proxy_delegated.")


if __name__ == "__main__":
    main()
