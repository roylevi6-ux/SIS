# SIS Manual Testing Guide

**Version:** 1.0
**Date:** 2026-02-23
**For:** VP Sales / QA manual testing
**Prerequisites:** FastAPI backend running on port 8000, Next.js frontend running on port 3000

---

## How to Use This Guide

Each test case has three parts:
- **Do**: Step-by-step click instructions
- **Expect**: What you should see if everything works
- **Watch for**: Specific failure modes and things that could go wrong

Check off each item as you complete it. If something fails, note the test number and what you observed.

---

## 0. Pre-Flight: Start the System

### 0.1 Start the Backend

- [ ] **Do**: Open a terminal and run:
  ```
  cd /Users/roylevierez/Documents/Sales/SIS
  python -m uvicorn sis.api.main:app --reload --port 8000
  ```
- [ ] **Expect**: Terminal shows `Uvicorn running on http://0.0.0.0:8000`. No import errors.
- [ ] **Watch for**: Missing environment variables (ANTHROPIC_API_KEY, etc.), import errors mentioning specific modules, port already in use.

### 0.2 Start the Frontend

- [ ] **Do**: Open a second terminal and run:
  ```
  cd /Users/roylevierez/Documents/Sales/SIS/frontend
  npm run dev
  ```
- [ ] **Expect**: Terminal shows `Ready` with URL `http://localhost:3000`.
- [ ] **Watch for**: Build errors, missing dependencies (`npm install` may be needed first).

### 0.3 Open the App

- [ ] **Do**: Open `http://localhost:3000` in your browser.
- [ ] **Expect**: The SIS dashboard loads with a sidebar on the left containing navigation links: Pipeline Overview, Deal Detail, Divergence View, Team Rollup, etc.
- [ ] **Watch for**: Blank page (check browser console for errors), sidebar not rendering, API connection failures shown in red.

### 0.4 Verify API Connectivity

- [ ] **Do**: Open `http://localhost:8000/docs` in a new tab.
- [ ] **Expect**: FastAPI's interactive Swagger docs page loads, showing all API endpoints grouped by tag (accounts, analyses, transcripts, gdrive, etc.).
- [ ] **Watch for**: 502/503 errors, CORS errors in the browser console when the frontend tries to call the backend.

---

## 1. Import Flow (Google Drive)

This is the primary way transcripts enter the system. The flow is: validate path, see accounts, preview calls, configure deal, import, analyze.

### 1.1 Navigate to Upload Page

- [ ] **Do**: Click "Upload Transcript" in the sidebar. You should land on a page with three tabs: "Google Drive", "Local Folder", "Paste Text".
- [ ] **Expect**: Google Drive tab is selected by default. There is a text input for "Google Drive Folder Path" and a "Scan" button.
- [ ] **Watch for**: Tabs not rendering, page showing a loading spinner indefinitely.

### 1.2 Enter and Validate a Google Drive Path

- [ ] **Do**: Paste your Google Drive path into the text field (e.g., `~/Library/CloudStorage/GoogleDrive-you@company.com/My Drive/Transcripts`). Click "Scan".
- [ ] **Expect**: A green checkmark and message like "Valid path. Found X account folders." appears below the input. An "Select Account" dropdown appears with account names and call counts.
- [ ] **Watch for**:
  - Red X with "Path not found" -- double-check the path exists on disk
  - Error message about permissions
  - If path was saved from a previous session, it may auto-populate -- verify it still works

### 1.3 Invalid Path Handling

- [ ] **Do**: Enter a clearly wrong path like `/nonexistent/path/here`. Click "Scan".
- [ ] **Expect**: A red error message appears: the path is invalid or not found. No account dropdown appears.
- [ ] **Watch for**: Unhandled exception, blank error message, or the UI freezing.

### 1.4 Select an Account and Preview Calls

- [ ] **Do**: From the account dropdown, select an account (e.g., "JD Sports" or "Japan Airlines").
- [ ] **Expect**: A table appears showing the most recent calls with three columns: Date, Title, and Transcript (checkmark or dash). The number of rows matches the "Max calls to import" setting (default 5).
- [ ] **Watch for**:
  - Calls appearing in wrong order (should be most recent first in the preview)
  - Missing call titles (should show the Gong call title, not just a date)
  - "Transcript" column showing dashes for calls that do have transcript files

### 1.5 Adjust Max Calls

- [ ] **Do**: Change the "Max calls to import" field from 5 to 3.
- [ ] **Expect**: The call preview table should update when you re-select the account, showing only 3 calls.
- [ ] **Watch for**: The number input accepting values below 1 or above 20, table not updating.

### 1.6 Configure Deal Type

- [ ] **Do**: In the "Deal Configuration" section below the calls table, set:
  - Deal Type: select "Expansion - Upsell" (or any type)
  - MRR Estimate: enter a number like `50000`
  - AE Owner: type a name
  - Team Lead: type a name
- [ ] **Expect**: All fields accept input normally. Deal Type dropdown shows all 5 options: New Logo, Expansion - Upsell, Expansion - Cross Sell, Expansion - Both, Renewal.
- [ ] **Watch for**: Deal type dropdown not opening, MRR field accepting negative numbers.

### 1.7 Import and Run Analysis

- [ ] **Do**: Click the "Import & Run Analysis" button at the bottom.
- [ ] **Expect**:
  1. Button changes to "Importing & Analyzing..." with a spinner
  2. After a few seconds, a green success banner appears: "Imported X calls for [Account Name]"
  3. The calls table and import button disappear
  4. The **Analysis Progress Detail** component appears, showing:
     - A progress bar (X/10 agents or X/11 for expansion deals)
     - A list of all agents with status icons (pending dash, spinning loader, green checkmark, or red X)
     - Each agent shows: name, elapsed time, token counts, cost
     - A running total of cost and time at the bottom
  5. After 60-120 seconds, all agents complete and you see "Analysis Complete" with a "View Deal Detail" link
- [ ] **Watch for**:
  - Import failing with an error message (check the red error box for details)
  - Analysis progress getting stuck on one agent for more than 60 seconds
  - SSE connection error: "Connection lost" message
  - Agent 0E appearing for non-expansion deals (it should only appear for expansion deal types)
  - Agent 0E NOT appearing for expansion deals (it should be listed as the first agent)
  - Total cost seeming unreasonable (should be roughly $0.30-$0.80 per run)

### 1.8 Deduplication on Re-Import

This tests that re-importing the same account does not create duplicate transcripts.

- [ ] **Do**: After a successful import, go back to the Upload page. Select the same Google Drive path, same account, and click "Import & Run Analysis" again.
- [ ] **Expect**:
  - The success banner shows "Imported 0 calls for [Account Name] (X already imported)" or "X skipped"
  - In the calls list, skipped calls appear with strikethrough text and "(skipped)" label
  - Analysis still runs on the existing transcripts
- [ ] **Watch for**:
  - Duplicate transcripts being created (check the deal detail page -- transcript count should not double)
  - "0 imported" but the skipped count is also 0 (something is wrong with dedup matching)
  - No "(skipped)" indicator -- the user needs to know WHY zero calls were imported

### 1.9 Rescan After Changes

- [ ] **Do**: While on the upload page with accounts loaded, click the "Rescan" button (small text link next to "Select Account").
- [ ] **Expect**: The account list refreshes. If you added new folders to Google Drive, they should appear.
- [ ] **Watch for**: Rescan clearing the selected account but not clearing the calls table.

---

## 2. Import Flow (Local Folder)

### 2.1 Local Folder Tab

- [ ] **Do**: Click the "Local Folder" tab on the upload page.
- [ ] **Expect**: Same layout as Google Drive tab: path input, Scan button, account selection, calls preview, deal config, import button.
- [ ] **Watch for**: Missing or broken UI elements compared to the Google Drive tab.

### 2.2 Scan a Local Folder

- [ ] **Do**: Enter a path to a local folder containing Gong JSON exports organized in account sub-folders. Click "Scan".
- [ ] **Expect**: Works identically to Google Drive: validates path, lists accounts, allows selection and import.
- [ ] **Watch for**: The same path working in Google Drive tab but failing in Local Folder tab (or vice versa) -- they should use the same backend validation.

---

## 3. Import Flow (Manual Paste)

### 3.1 Manual Paste Tab

- [ ] **Do**: Click the "Paste Text" tab on the upload page.
- [ ] **Expect**: A form with: Account dropdown (pre-existing accounts), Call Date picker, Duration input, large text area for pasting transcript text, and "Upload Transcript" button.
- [ ] **Watch for**: Account dropdown being empty (means no accounts exist yet -- you need to import or create one first).

### 3.2 Manual Upload

- [ ] **Do**: Select an existing account, set a date, paste any text into the transcript field, click "Upload Transcript".
- [ ] **Expect**: Green success message showing "Transcript uploaded successfully!" with token count.
- [ ] **Watch for**: Upload succeeding but not showing token count, upload failing without a clear error message.

### 3.3 Manual Upload Validation

- [ ] **Do**: Try to submit the form with an empty transcript text field.
- [ ] **Expect**: The "Upload Transcript" button should be disabled (greyed out) when required fields are empty.
- [ ] **Watch for**: Button being clickable despite empty fields, no visual indication of which fields are required.

---

## 4. Analysis Flow & SSE Progress

### 4.1 Analysis from Upload Page

- [ ] **Do**: Complete an import (tests 1.7 above). Observe the progress component.
- [ ] **Expect**: The analysis progress component shows real-time updates:
  1. All agents start as "pending" (dash icon)
  2. Agents 1-8 (and 0E for expansion) move to "running" (spinner) in parallel
  3. As each agent completes, it switches to a green checkmark with elapsed time, token counts, and cost
  4. After all parallel agents finish, Agent 9 (Open Discovery) starts
  5. After Agent 9, Agent 10 (Synthesis) starts
  6. On completion: green "Analysis Complete" banner with total cost and "View Deal Detail" button
- [ ] **Watch for**:
  - Agents appearing to run sequentially instead of in parallel (Agents 1-8 should run simultaneously)
  - Agent 9 starting before all of Agents 1-8 complete
  - Agent 10 starting before Agent 9 completes
  - Progress bar not updating (stuck at 0%)
  - Token counts or costs showing as 0 or null for completed agents

### 4.2 Analysis from Analyze Page

- [ ] **Do**: Navigate to the "Run Analysis" page via the sidebar. Select an account that has transcripts but needs re-analysis. Click "Run Analysis".
- [ ] **Expect**: Same progress component as 4.1 above. The page should show analysis running without needing to go through the import flow.
- [ ] **Watch for**: "No active transcripts" error for an account you know has transcripts.

### 4.3 Expansion Deal Agent List

- [ ] **Do**: Import an account with Deal Type set to any "Expansion" type. Observe the analysis progress.
- [ ] **Expect**: 11 agents appear in the progress list (Agent 0E: Account Health & Sentiment, plus the standard 10). Agent 0E runs in parallel with Agents 1-8.
- [ ] **Watch for**: Only 10 agents appearing for an expansion deal (Agent 0E missing), or Agent 0E appearing for a "New Logo" deal type.

### 4.4 Analysis Failure Handling

- [ ] **Do**: If possible, trigger a failure (e.g., temporarily revoke the API key, or analyze an account with no transcripts).
- [ ] **Expect**:
  - Failed agents show a red X icon with an error message
  - If some agents succeed but others fail, the status shows "Partial results -- some agents failed" with a "View Results" link
  - If the entire pipeline fails, the status shows "Analysis failed" with error details
- [ ] **Watch for**: Silent failures (no error shown), the UI freezing after a failure, no way to retry.

---

## 5. Pipeline Overview (Dashboard)

### 5.1 Navigate to Pipeline

- [ ] **Do**: Click "Pipeline Overview" in the sidebar.
- [ ] **Expect**: The page loads with:
  - **Header**: "Pipeline Overview" title with total deal count
  - **Four summary cards**: Healthy (green), At Risk (amber), Critical (red), Unscored (grey) -- each showing deal count and MRR total
  - **Tab bar**: All, Healthy, At Risk, Critical, Unscored -- each showing count in parentheses
  - **Deal table**: Sortable columns for Account, MRR, Stage, Health, Momentum, AI Forecast, IC Forecast, Last Call
- [ ] **Watch for**: Summary card counts not matching the tab counts, MRR totals being $0 when deals have MRR set.

### 5.2 Health Tier Grouping

- [ ] **Do**: Note the summary cards. Then click each tab (Healthy, At Risk, Critical, Unscored).
- [ ] **Expect**:
  - Healthy tab: deals with health score 70+
  - At Risk tab: deals with health score 45-69
  - Critical tab: deals with health score below 45
  - Unscored tab: deals that have not been analyzed yet
- [ ] **Watch for**: A deal appearing in the wrong tier, the "All" tab count not equaling the sum of the other four.

### 5.3 Column Sorting

- [ ] **Do**: Click each column header in the deal table: Account, MRR, Stage, Health, Momentum, AI Forecast, IC Forecast, Last Call.
- [ ] **Expect**: Each click sorts the table by that column. Clicking the same column again reverses the sort direction (ascending/descending). Active sort column shows an up/down arrow.
- [ ] **Watch for**: Sorting not working on a specific column, null/empty values not sorting to the end, sort arrow not updating visually.

### 5.4 Team Filter

- [ ] **Do**: If you have deals with different team names, use the team filter dropdown in the top-right corner.
- [ ] **Expect**: The dropdown lists all unique team names. Selecting a team filters both the summary cards AND the deal table to show only that team's deals.
- [ ] **Watch for**: Team filter not updating the summary card numbers, "All Teams" option not clearing the filter.

### 5.5 Deal Row Click-Through

- [ ] **Do**: Click on any deal row in the table.
- [ ] **Expect**: You are navigated to the deal detail page (`/deals/[id]`).
- [ ] **Watch for**: Click not working, navigating to wrong deal, the entire row being clickable (it should be).

### 5.6 Divergence Warning Icon

- [ ] **Do**: If any deal has a divergence flag (IC forecast differs from AI forecast), look for the warning triangle icon next to the account name in the pipeline table.
- [ ] **Expect**: A small amber warning triangle icon appears. Hovering over it shows a tooltip: "IC and AI forecasts diverge".
- [ ] **Watch for**: Divergence icon missing for a deal you know is divergent, icon appearing when there is no divergence.

### 5.7 Empty Pipeline State

- [ ] **Do**: If you have no accounts at all, navigate to Pipeline Overview.
- [ ] **Expect**: Summary cards show 0 for all tiers. The "All" tab shows a message like "No deals to display."
- [ ] **Watch for**: Error instead of an empty state, summary cards showing NaN or undefined.

---

## 6. Deal Detail Page

### 6.1 Navigate to Deal Detail

- [ ] **Do**: From the Pipeline Overview, click on a deal that has been analyzed. (Or navigate directly to `/deals/[account_id]`.)
- [ ] **Expect**: The deal detail page loads with:
  - **Back link**: "Back to Pipeline" arrow link at the top
  - **Account name** as the page title
  - **Status row**: Health badge (colored score), Momentum indicator (arrow), Stage number and name
  - **Forecast row**: AI Forecast badge, IC Forecast badge, Confidence percentage
  - **Meta info**: Deal type badge (for expansion deals), AE, TL, Team, MRR, Prior Contract Value (for expansion)
  - **Give Feedback** button (top right)
- [ ] **Watch for**: Missing data fields showing "undefined" or "null" instead of "--" or being hidden.

### 6.2 Call Timeline

- [ ] **Do**: Look at the "Call Timeline" section (appears right below the header separator).
- [ ] **Expect**:
  - A horizontal timeline with dots for each call
  - **Analyzed calls**: larger purple circle with phone icon
  - **Not analyzed calls**: smaller grey dot
  - **Legend**: shows counts of analyzed vs not-analyzed
  - **Date labels**: below the timeline axis, showing dates. For short ranges (<90 days), each call date is labeled. For longer ranges, month boundaries are shown.
  - **Tooltips**: hover over any dot to see: call title (if set), full date, duration, external participants, internal participants, and "Included in analysis" for analyzed calls
  - **Today marker**: a vertical red dotted line labeled "Today" (if today falls within the timeline range)
  - **Short call title labels**: below each dot, a truncated version of the call title (max ~12 chars)
- [ ] **Watch for**:
  - Dots overlapping so they are unclickable (should have minimum spacing)
  - Date labels overlapping (should have 8% minimum spacing filter)
  - Today marker appearing outside the timeline range
  - Call titles not appearing in tooltips
  - All dots showing as "not analyzed" even though analysis ran (verify the `analyzed` flag is correctly set on transcripts included in the latest analysis run)

### 6.3 Deal Memo

- [ ] **Do**: Scroll down to the "Deal Memo" section.
- [ ] **Expect**: A card containing 3-5 paragraphs of narrative text summarizing the deal state, stakeholders, risks, momentum, and unusual signals.
- [ ] **Watch for**: Empty memo (just a blank card), raw JSON instead of formatted text, extremely short memo (less than 2 paragraphs suggests the synthesis agent under-performed).

### 6.4 Health Score Breakdown

- [ ] **Do**: Look at the "Health Score Breakdown" section.
- [ ] **Expect**: A visual breakdown showing 8 components (or 9 for expansion deals): economic buyer, stage, momentum, technical, competitive, stakeholder, commitment, commercial. Each should show score/max and have a progress bar.
- [ ] **Watch for**:
  - Component scores not adding up to the total health score
  - All components showing 0 (suggests synthesis output parsing failed)
  - Missing component names or labels
  - For expansion deals: the 9th component "Account Relationship Health" should appear (from Agent 0E)

### 6.5 Actions and Risks (Two-Column Layout)

- [ ] **Do**: Look at the two-column section showing "Recommended Actions" on the left and "Risk Signals" on the right.
- [ ] **Expect**:
  - **Actions**: Up to 5 action items, each with an owner/assignee and the action text. Format: "**Owner**: action description"
  - **Risks**: Up to 5 risk items, each with a severity tag and risk description. Format: "[severity] risk description"
- [ ] **Watch for**: Actions or risks showing as raw JSON objects instead of formatted text, empty lists showing no placeholder text.

### 6.6 Positive Signals and Contradictions

- [ ] **Do**: Look at the second two-column section below actions/risks.
- [ ] **Expect**:
  - **Positive Signals**: Green "+" icon + signal text, each with evidence summary
  - **Contradictions**: Purple lightning icon + contradiction description with dimension, detail, and resolution
- [ ] **Watch for**: Contradictions section always being empty (it should surface conflicting agent findings -- if agents never contradict, something may be too agreeable in the prompts).

### 6.7 Forecast Divergence Section

- [ ] **Do**: If the deal has a divergence flag (IC forecast differs from AI forecast), look for the "Forecast Divergence" card with amber border.
- [ ] **Expect**: An amber-bordered card with a warning icon and explanation text describing why AI and IC forecasts differ.
- [ ] **Watch for**: Divergence card appearing when AI and IC forecasts are the same, or NOT appearing when they differ.

### 6.8 Key Unknowns

- [ ] **Do**: Look for the "Key Unknowns" section.
- [ ] **Expect**: A bulleted list of 1-5 items that the system could not determine from the transcripts (e.g., "Economic buyer engagement level unclear", "Timeline for legal review unknown").
- [ ] **Watch for**: Empty list even when the confidence score is low (low confidence should correlate with key unknowns).

### 6.9 Forecast Rationale

- [ ] **Do**: Look for the "Forecast Rationale" section.
- [ ] **Expect**: A paragraph explaining what would need to change for the AI forecast category to move up or down (e.g., "To move from Pipeline to Best Case, the economic buyer needs to appear on a call and commercial terms need to be discussed").
- [ ] **Watch for**: Rationale being generic/boilerplate rather than deal-specific.

### 6.10 Per-Agent Analysis Cards

- [ ] **Do**: Scroll to the "Per-Agent Analysis" section. Each agent should have a collapsible card.
- [ ] **Expect**:
  - Each agent card shows: agent name, confidence level, and a collapse/expand toggle
  - Expanding a card shows: narrative text (2-4 paragraphs), structured findings, evidence quotes, data gaps
  - For expansion deals: Agent 0E (Account Health & Sentiment) card should appear
  - Agent order: 0E (if expansion), 1 through 9 (Agent 10/Synthesis output is shown as the Deal Memo above, not as a card)
- [ ] **Watch for**:
  - Agent cards not expanding on click
  - Missing agent cards (count should be 9 for new-logo or 10 for expansion)
  - Evidence quotes being empty when the narrative makes factual claims
  - Confidence levels all being identical (each agent should have different confidence based on available data)

### 6.11 Assessment Timeline (Deal Timeline)

- [ ] **Do**: Scroll down to see the assessment timeline section (titled "Deal Timeline" or "Assessment Timeline").
- [ ] **Expect**: If the deal has been analyzed multiple times, a timeline showing health score changes over time with dots for each analysis run.
- [ ] **Watch for**: Timeline showing only one point when multiple analysis runs exist.

### 6.12 Analysis History

- [ ] **Do**: Look at the "Analysis History" section.
- [ ] **Expect**: A list of all analysis runs for this account, showing: status badge (completed/failed/running), date, and run ID (first 8 chars).
- [ ] **Watch for**: Runs stuck in "running" status that should have completed or failed, missing cost data.

### 6.13 Transcript List

- [ ] **Do**: Scroll to the "Transcripts" section at the bottom.
- [ ] **Expect**: A list showing each transcript with: date, active/inactive badge, duration, token count.
- [ ] **Watch for**: Transcripts marked as "Inactive" without explanation (this happens when >5 transcripts exist and older ones are archived), missing duration or token count data.

---

## 7. IC Forecast & Divergence

### 7.1 Set IC Forecast

- [ ] **Do**: Navigate to the Forecast page (`/forecast` in sidebar, labeled "AI vs IC Forecast"). Find a deal in the table. Note the IC Forecast column.

  Alternatively, use the API directly: Open `http://localhost:8000/docs`, find `PUT /api/accounts/{account_id}`, and set `ic_forecast_category` to one of: "Commit", "Best Case", "Pipeline", "Upside", "At Risk", "No Decision Risk".
- [ ] **Expect**: The IC forecast updates and appears in the pipeline overview, deal detail page, and forecast comparison page.
- [ ] **Watch for**: IC forecast not persisting after page refresh, invalid category values being accepted.

### 7.2 Trigger Divergence

- [ ] **Do**: Set the IC forecast to a value that DIFFERS from the AI forecast (e.g., if AI says "Pipeline", set IC to "Commit").
- [ ] **Expect**:
  - The deal now shows a divergence warning triangle in the Pipeline Overview
  - The Deal Detail page shows the "Forecast Divergence" amber card with an explanation
  - The Divergence View page (`/divergence`) now lists this deal
- [ ] **Watch for**: Divergence not triggering when forecasts differ, or divergence persisting after you set IC to match AI.

### 7.3 Clear Divergence

- [ ] **Do**: Set the IC forecast to match the AI forecast exactly.
- [ ] **Expect**: The divergence warning disappears from Pipeline Overview, Deal Detail, and Divergence View.
- [ ] **Watch for**: Stale divergence flags remaining after the IC forecast is changed.

### 7.4 Divergence View Page

- [ ] **Do**: Navigate to "Divergence View" in the sidebar (also called "Forecast Alignment Check").
- [ ] **Expect**:
  - Title: "Forecast Alignment Check" (NOT "AI Disagrees" -- per PRD safety rules)
  - Subtitle shows count of divergent deals
  - Table columns: Account, MRR, AI Forecast, IC Forecast, Health, Explanation
  - Deals sorted by MRR descending (highest value impact first)
  - Team filter dropdown (if multiple teams exist)
- [ ] **Watch for**: Title saying anything other than "Forecast Alignment Check", deals without IC forecast appearing in the divergence list, explanation column being empty.

### 7.5 Forecast Comparison Page

- [ ] **Do**: Navigate to "AI vs IC Forecast" in the sidebar.
- [ ] **Expect**:
  - **Summary stats**: Total Deals, Divergent count, Weighted Pipeline total
  - **Bar chart**: Grouped bar chart showing AI vs IC distribution across forecast categories (Commit, Best Case, Pipeline, Upside, At Risk, No Decision Risk)
  - **Deal table**: All deals with Account, MRR, AI Forecast, IC Forecast, Health, Momentum, Divergence badge
  - Team filter dropdown
- [ ] **Watch for**: Bar chart not rendering (check if recharts is installed), Weighted Pipeline total being $0 when deals have MRR, chart categories not matching the 6 forecast categories.

---

## 8. Expansion Deals

### 8.1 Create an Expansion Deal

- [ ] **Do**: On the Upload page, select an account folder and set Deal Type to "Expansion - Upsell". Enter a Prior Contract Value if the field appears. Click "Import & Run Analysis".
- [ ] **Expect**:
  - The import succeeds
  - During analysis, 11 agents appear (Agent 0E included)
  - Agent 0E: "Account Health & Sentiment" runs in parallel with Agents 1-8
- [ ] **Watch for**: Agent 0E not appearing, "Prior Contract Value" field not being visible.

### 8.2 Expansion Deal Detail

- [ ] **Do**: After analysis completes, click "View Deal Detail".
- [ ] **Expect**:
  - A blue badge showing the deal type (e.g., "Expansion: Upsell") in the header meta info
  - "Prior: $XK" displayed if a prior contract value was set
  - Agent 0E card visible in the Per-Agent Analysis section
  - Health score breakdown may include a 9th component for account relationship health
- [ ] **Watch for**:
  - Deal type badge missing or showing the raw value "expansion_upsell" instead of "Expansion: Upsell"
  - Agent 0E card missing from per-agent analysis
  - Health score components not including account relationship health for expansion deals

### 8.3 New Logo vs Expansion Pipeline

- [ ] **Do**: Compare the pipeline overview for a new-logo deal vs an expansion deal.
- [ ] **Expect**: Both appear in the same pipeline view. The expansion deal has a deal type badge. Health scores for expansion deals should generally be higher than the same deal analyzed as new-logo (because expansion calibration is more lenient).
- [ ] **Watch for**: Expansion deals being systematically under-scored (the whole point of the expansion pipeline is to avoid this).

---

## 9. Delta Annotations (Re-Analysis Comparison)

### 9.1 Run a Second Analysis

- [ ] **Do**: Take an account that has already been analyzed. Go to the "Run Analysis" page, select it, and run analysis again (without adding new transcripts).
- [ ] **Expect**: The pipeline runs. After completion, the deal detail page may show delta badges next to changed fields.
- [ ] **Watch for**: Analysis failing because "no active transcripts" (transcripts should still be there from the first run).

### 9.2 View Delta Badges

- [ ] **Do**: After re-analysis, navigate to the deal detail page.
- [ ] **Expect**: If any fields changed between the two analysis runs, you should see delta badges:
  - **Numeric changes** (health score, confidence): shown as "72 -> 78 (+6)" in green (improvement) or red (decline)
  - **Categorical changes** (stage, forecast, momentum): shown as "Discovery -> Validation" in blue
  - Delta badges appear next to: Health score, Momentum, Stage, AI Forecast, Confidence
- [ ] **Watch for**:
  - Delta badges always showing (they should only appear when values actually changed)
  - Delta badges never showing (suggests the delta API is not returning data)
  - Numeric deltas with wrong sign (positive change in score should be green with +)

### 9.3 No Delta on First Analysis

- [ ] **Do**: Check a deal that has only been analyzed once.
- [ ] **Expect**: No delta badges appear anywhere (there is no previous run to compare against).
- [ ] **Watch for**: Delta badges showing "undefined -> 72" or similar partial data.

---

## 10. Chat Interface

### 10.1 Navigate to Chat

- [ ] **Do**: Click "Chat" in the sidebar.
- [ ] **Expect**: A chat interface with a text input at the bottom and an empty message area above.
- [ ] **Watch for**: Chat page not loading, input field not being interactive.

### 10.2 Ask About a Specific Deal

- [ ] **Do**: Type: "Tell me about [Account Name]" (use a real account name that has been analyzed). Press Enter.
- [ ] **Expect**: The AI responds with deal-specific information: health score, stage, momentum, forecast category, key risks, and positive signals. The response should reference actual data from the pipeline.
- [ ] **Watch for**:
  - AI hallucinating data about accounts that do not exist
  - AI giving generic responses without referencing specific health scores or risks
  - Response taking more than 15 seconds (should be fast since it queries stored data, not re-running the pipeline)
  - Error message about API key or model not found

### 10.3 Cross-Pipeline Query

- [ ] **Do**: Type: "Which deals are at risk?" or "Which deals need attention?"
- [ ] **Expect**: The AI lists deals in the Critical and At Risk tiers with their health scores, and may also flag deals with declining momentum.
- [ ] **Watch for**: The AI missing deals that are clearly at risk, or including healthy deals in the at-risk list.

### 10.4 Follow-Up Question

- [ ] **Do**: After getting a response about a specific deal, ask a follow-up: "What about their timeline?" or "What are the next steps?"
- [ ] **Expect**: The AI maintains context from the previous question and responds about the same deal without needing you to repeat the account name.
- [ ] **Watch for**: The AI losing context and asking "which deal are you referring to?"

### 10.5 Forecast Comparison Query

- [ ] **Do**: Type: "Compare AI vs IC forecast" or "Show me the forecast comparison".
- [ ] **Expect**: The AI summarizes the aggregate forecast comparison, listing deals where AI and IC differ.
- [ ] **Watch for**: The AI saying there is no forecast data when IC forecasts have been set.

---

## 11. Additional Pages

### 11.1 Team Rollup

- [ ] **Do**: Navigate to "Team Rollup" in the sidebar.
- [ ] **Expect**: A view showing aggregate health metrics per team: deal count, average health score, total MRR, divergent deal count.
- [ ] **Watch for**: Teams with 0 deals appearing in the rollup, average health score being NaN.

### 11.2 Meeting Prep

- [ ] **Do**: Navigate to "Meeting Prep" in the sidebar. Select an account that has been analyzed.
- [ ] **Expect**: A pre-call brief with sections: Key Topics to Raise, Questions to Ask, Risks to Watch, Actions to Follow Up On, Positive Signals to Leverage.
- [ ] **Watch for**: Empty sections when the deal clearly has risks or unknowns, the page showing "No scored accounts" when accounts have been analyzed.

### 11.3 Cost Monitor

- [ ] **Do**: Navigate to "Cost Monitor" in the sidebar.
- [ ] **Expect**: A view showing total API costs across all analysis runs, possibly broken down by agent or account.
- [ ] **Watch for**: Costs showing $0.00 when analyses have been run.

### 11.4 Feedback Dashboard

- [ ] **Do**: Navigate to "Feedback Dashboard" in the sidebar.
- [ ] **Expect**: A view showing all submitted score feedback, filterable by status (pending/accepted/rejected).
- [ ] **Watch for**: Feedback submissions not appearing after being submitted from the deal detail page.

---

## 12. Edge Cases & Error Handling

### 12.1 Long Call Titles

- [ ] **Do**: If you have a call with a very long title (30+ characters), check how it displays in:
  - The calls preview table on the upload page
  - The call timeline dots (should be truncated to ~12 chars with ellipsis)
  - The tooltip on hover (should show full title)
- [ ] **Expect**: Long titles are truncated in the timeline with "..." but fully visible in the tooltip.
- [ ] **Watch for**: Title overflowing and breaking the layout, tooltip not showing the full title.

### 12.2 Account with No Transcripts

- [ ] **Do**: Create an account via the API (`POST /api/accounts/`) without uploading any transcripts. Navigate to its deal detail page.
- [ ] **Expect**: The page shows the account name and a message like "No assessment available. Upload transcripts and run an analysis."
- [ ] **Watch for**: Error/crash instead of empty state, a misleading "Run Analysis" button that would fail.

### 12.3 Account with No Assessment (Transcripts but Not Analyzed)

- [ ] **Do**: Upload a transcript to an account but do not run analysis. Navigate to the deal detail page.
- [ ] **Expect**: The Call Timeline shows the uploaded transcript as a grey (not analyzed) dot. The "No assessment available" message appears. The transcript is listed in the Transcripts section.
- [ ] **Watch for**: The Call Timeline not rendering when there are transcripts but no assessment.

### 12.4 Many Transcripts (>5)

- [ ] **Do**: Import more than 5 transcripts for an account (set max calls to 8 or higher).
- [ ] **Expect**: The system imports all calls, but only the 5 most recent are marked as "active" for analysis. Older transcripts appear in the transcript list with an "Inactive" badge.
- [ ] **Watch for**: All transcripts being active (the 5-transcript limit should be enforced), inactive transcripts being included in analysis.

### 12.5 Backend Down

- [ ] **Do**: Stop the FastAPI backend (`Ctrl+C` in the backend terminal). Then try to load the Pipeline Overview.
- [ ] **Expect**: The frontend shows an error state: "Failed to load pipeline data" with a descriptive error message.
- [ ] **Watch for**: Blank page with no error indication, infinite loading spinner with no timeout.

### 12.6 Single Transcript Account

- [ ] **Do**: Import an account with only 1 transcript and run analysis.
- [ ] **Expect**:
  - Analysis completes (the system should work with 1 transcript)
  - The assessment should have a lower confidence score (sparse data)
  - Momentum should be "Unknown" or "Stable" (cannot compute momentum from 1 call)
  - The Call Timeline shows a single dot
- [ ] **Watch for**: Analysis failing for single-transcript accounts, momentum showing "Improving" or "Declining" when there is only one data point.

---

## 13. Re-Import Cleaned Accounts (JD Sports & Japan Airlines)

These two accounts were recently cleaned (data deleted) and need fresh import and analysis.

### 13.1 Re-Import JD Sports

- [ ] **Do**: Go to Upload page. Navigate to your Google Drive or local folder. Select "JD Sports". Review the calls preview. Set the appropriate Deal Type. Click "Import & Run Analysis".
- [ ] **Expect**:
  - All calls import as new (since the old data was cleaned, dedup should not skip any)
  - "Imported X calls" with 0 skipped
  - Analysis runs successfully on all imported calls
- [ ] **Watch for**: Dedup incorrectly skipping calls that should be fresh (if gong_call_id matching is too aggressive), or importing calls that should not be there.

### 13.2 Re-Import Japan Airlines

- [ ] **Do**: Same process as 13.1 but for "Japan Airlines".
- [ ] **Expect**: Same behavior -- all calls imported fresh, analysis completes.
- [ ] **Watch for**: Same issues as 13.1.

### 13.3 Verify Both in Pipeline

- [ ] **Do**: After both accounts are imported and analyzed, go to Pipeline Overview.
- [ ] **Expect**: Both JD Sports and Japan Airlines appear in the deal table with health scores, stages, momentum, and forecast categories.
- [ ] **Watch for**: Missing deals, deals showing as "Unscored" despite analysis having completed.

---

## 14. Cross-Feature Integration Checks

### 14.1 End-to-End New Logo Flow

- [ ] **Do**: Complete this full flow:
  1. Upload page: Import a new-logo account with 3+ transcripts
  2. Watch the analysis progress (all 10 agents)
  3. Click "View Deal Detail" when done
  4. Read the deal memo, check health breakdown
  5. Go to Pipeline Overview, find the deal, verify data matches
  6. Set an IC forecast via the API that differs from AI forecast
  7. Check Divergence View -- the deal should appear
  8. Go to Chat, ask about the deal
  9. Go to Meeting Prep, select the deal
- [ ] **Expect**: All steps work without errors. Data is consistent across all views (health score, forecast, stage, etc. match everywhere).
- [ ] **Watch for**: Health score showing different values on different pages (data inconsistency), forecast categories not matching.

### 14.2 End-to-End Expansion Flow

- [ ] **Do**: Same as 14.1 but with Deal Type set to "Expansion - Cross Sell" and a prior contract value.
- [ ] **Expect**: Same as 14.1, plus: Agent 0E appears in analysis, deal type badge shows on deal detail, account relationship health appears in health breakdown.
- [ ] **Watch for**: Missing expansion-specific features anywhere in the flow.

### 14.3 Re-Analysis Delta Flow

- [ ] **Do**:
  1. Analyze an account (first run)
  2. Note the health score, stage, and forecast
  3. Run analysis again (second run)
  4. Check the deal detail page for delta badges
- [ ] **Expect**: If any values changed between runs, delta badges appear. If values are the same, no delta badges appear.
- [ ] **Watch for**: Delta badges showing on the first-ever analysis (impossible -- nothing to compare to).

---

## Test Completion Checklist

| Area | Tests | Pass | Fail | Skip |
|------|-------|------|------|------|
| Pre-Flight (0.x) | 4 | | | |
| Import - Drive (1.x) | 9 | | | |
| Import - Local (2.x) | 2 | | | |
| Import - Manual (3.x) | 3 | | | |
| Analysis & SSE (4.x) | 4 | | | |
| Pipeline Overview (5.x) | 7 | | | |
| Deal Detail (6.x) | 13 | | | |
| IC Forecast & Divergence (7.x) | 5 | | | |
| Expansion Deals (8.x) | 3 | | | |
| Delta Annotations (9.x) | 3 | | | |
| Chat (10.x) | 5 | | | |
| Additional Pages (11.x) | 4 | | | |
| Edge Cases (12.x) | 6 | | | |
| Re-Import Cleaned (13.x) | 3 | | | |
| Integration (14.x) | 3 | | | |
| **TOTAL** | **74** | | | |

---

## Notes

- **Estimated time**: Full test suite takes approximately 2-3 hours. The analysis pipeline runs (~60-120 seconds per account) are the bottleneck.
- **API costs**: Running analysis on 3-4 accounts will cost approximately $1.50-$3.00 in LLM API fees.
- **Order matters for some tests**: Tests in section 9 (Delta) require section 4 (Analysis) to have been completed first. Tests in section 7 (Divergence) require section 5 (Pipeline) to have data.
- **If something fails**: Note the test number, what you expected, and what actually happened. Screenshots are very helpful. Check the backend terminal for Python error logs.
