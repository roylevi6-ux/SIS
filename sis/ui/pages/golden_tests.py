"""Golden Tests — regression test runner and baseline management per PRD Sec 7.11.

Run regression tests, view results, and create baselines from accounts.
"""

import streamlit as st

from sis.testing.golden_test import (
    run_all_golden_tests,
    load_golden_set,
    create_baseline,
)
from sis.services.account_service import list_accounts


def render():
    st.title("Golden Tests")
    st.caption("Regression gates for deal assessment quality — 4 automated checks")

    # Show toast from previous rerun
    if st.session_state.get("_gt_toast"):
        st.toast(st.session_state.pop("_gt_toast"))

    # --- Run Regression Tests ---
    st.subheader("Run Regression Tests")
    col1, col2 = st.columns([1, 3])
    with col1:
        run_clicked = st.button("Run Regression Tests", type="primary")
    with col2:
        fixtures = load_golden_set()
        st.caption(f"{len(fixtures)} golden fixtures loaded")

    if run_clicked:
        if not fixtures:
            st.warning("No golden fixtures found. Create baselines first.")
        else:
            with st.spinner("Running regression tests..."):
                results = run_all_golden_tests()

            # Summary
            passed = sum(1 for r in results if r["status"] == "PASS")
            warned = sum(1 for r in results if r["status"] == "WARN")
            failed = sum(1 for r in results if r["status"] == "FAIL")
            skipped = sum(1 for r in results if r["status"] == "SKIP")

            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.metric("Passed", passed)
            with mc2:
                st.metric("Warnings", warned)
            with mc3:
                st.metric("Failed", failed)
            with mc4:
                st.metric("Skipped", skipped)

            st.divider()

            # Detail table
            for r in results:
                if r["status"] == "PASS":
                    status_icon = ":green[PASS]"
                elif r["status"] == "WARN":
                    status_icon = ":orange[WARN]"
                elif r["status"] == "FAIL":
                    status_icon = ":red[FAIL]"
                else:
                    status_icon = ":gray[SKIP]"

                with st.expander(f"{status_icon} {r['account_name']} ({r['fixture_id']})"):
                    if r.get("reason"):
                        st.info(r["reason"])
                    for g in r.get("gates", []):
                        gc1, gc2, gc3, gc4 = st.columns(4)
                        with gc1:
                            st.text(g["gate"])
                        with gc2:
                            st.text(f"Threshold: {g['threshold']}")
                        with gc3:
                            st.text(f"Actual: {g['actual']}")
                        with gc4:
                            if g["status"] == "PASS":
                                st.markdown(":green[PASS]")
                            elif g["status"] == "WARN":
                                st.markdown(":orange[WARN]")
                            else:
                                st.markdown(":red[FAIL]")

            # Store results in session state for reference
            st.session_state["_gt_last_results"] = results

    st.divider()

    # --- Create Baseline ---
    st.subheader("Create Baseline from Account")
    accounts = list_accounts()
    scored = [a for a in accounts if a.get("health_score") is not None]

    if scored:
        names = [a["account_name"] for a in scored]
        selected = st.selectbox("Select Account", names, key="gt_account")
        account = scored[names.index(selected)]

        if st.button("Create Golden Baseline"):
            try:
                fixture = create_baseline(account["id"])
                st.session_state["_gt_toast"] = f"Created baseline: {fixture['fixture_id']}"
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("No scored accounts. Run analysis first.")

    st.divider()

    # --- Current Fixtures ---
    st.subheader("Current Golden Set")
    if fixtures:
        fixture_data = [
            {
                "Fixture": f["fixture_id"],
                "Account": f["account_name"],
                "Health": f["baseline"]["health_score"],
                "Forecast": f["baseline"]["ai_forecast_category"],
                "Stage": f["baseline"]["inferred_stage"],
                "Confidence": f["baseline"]["overall_confidence"],
                "Created": f["created_at"][:10],
            }
            for f in fixtures
        ]
        st.dataframe(fixture_data, use_container_width=True, hide_index=True)
    else:
        st.info("No golden fixtures yet. Create baselines from scored accounts above.")
