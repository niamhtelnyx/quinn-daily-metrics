# PRD: Auto-SFDC Meeting Sync

## RALPH (Request)

**Requester:** Ian Reit, COO
**Problem:** Sales reps consistently fail to update Salesforce after meetings. Meeting notes, deal signals, next steps, competitor intel, and contact data are lost — degrading pipeline accuracy and forecast reliability.
**Impact:** Incomplete SFDC data → bad forecasts → missed follow-ups → lost revenue. Every unlogged meeting is a blind spot for managers and a broken handoff for anyone who touches the deal next.
**Ask:** Automated system that captures meeting transcripts, extracts structured deal data, and pushes it into SFDC with minimal rep effort. Must work org-wide (not opt-in), handle net-new prospects with no existing SFDC record, and include human-in-the-loop validation during early rollout.

---

## Non-Goals

- **Does not replace Gong/Chorus** — this is CRM hygiene automation, not conversation intelligence or coaching
- **Does not change Forecast Category** — forecast fields are manager-owned, never touched
- **Does not auto-email customers** — no outbound communication of any kind
- **Does not auto-close or auto-win deals** — stage changes always require rep confirmation
- **Does not store raw transcripts in SFDC** — summaries and structured fields only (transcript stays in Fellow)

---

## TEST (Evaluate)

### Assumptions to Validate

| # | Assumption | Test | Pass Criteria |
|---|-----------|------|---------------|
| 1 | Fellow transcripts contain enough signal to extract MEDPICC fields | Run extraction on 20 real transcripts, have reps grade accuracy | >80% accuracy on extracted fields |
| 2 | We can reliably match meetings to SFDC Opportunities | Test matching logic against 50 recent meetings with known opp associations | >85% correct match rate |
| 3 | Reps will engage with Slack approval flow | Track push/edit/skip rates during Phase 2 | >70% response rate within 24h |
| 4 | Auto-created Leads from net-new calls are useful, not noisy | Track how many auto-created Leads convert vs. get junked | <20% junk rate |
| 5 | Fellow org-wide API/webhook access is available | Confirm with IT/RevOps | Binary: yes/no |

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Fellow API doesn't support org-wide webhooks | High | Fallback: GCal event trigger + Fellow API poll. Abstract transcript source so vendor is swappable. |
| Fellow is single point of failure for transcripts | High | Transcript-source abstraction layer from day 1. Interface: `get_transcript(meeting_id) → TranscriptResult`. Swap to Otter, Gong, or raw audio+Whisper without changing downstream. |
| Reps ignore Slack notifications (same laziness, different channel) | Medium | 24h auto-push + manager visibility report |
| Bad extraction quality erodes trust early | High | Phase 1 is read-only; reps see quality before writes are enabled |
| SFDC field conflicts with existing RevOps automation | Medium | Map all existing flows with SFDC admin before writes. Full field mapping spec below. |
| Internal meetings misclassified as external | Low | Filter: skip meetings with zero external attendees |
| Sensitive pricing/incident details visible in Slack summaries | Medium | Security/permissions matrix below |

---

## Idempotency and Deduplication

### Write Idempotency

Every sync operation is keyed on a composite idempotency key:

```
idempotency_key = hash(fellow_meeting_id + transcript_version + extraction_schema_version)
```

| Scenario | Behavior |
|----------|----------|
| Same meeting processed twice (retry, webhook replay) | Idempotency key match → skip, log as duplicate |
| Transcript updated by Fellow (late joiner, corrected speaker labels) | New transcript_version → re-extract, diff against previous, only update changed fields |
| Extraction schema changes (we improve the prompt) | New schema_version → re-extract, present as "updated extraction" in Slack, don't auto-push |
| Slack button clicked twice | Slack interaction_id dedup → second click returns "already processed" |

### Storage

All processed meetings tracked in a `sync_ledger` table:

```sql
CREATE TABLE sync_ledger (
    id UUID PRIMARY KEY,
    fellow_meeting_id TEXT NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    transcript_version TEXT,
    extraction_json JSONB,
    match_result JSONB,          -- {type: "opp"|"account"|"lead"|"none", sfdc_id, confidence}
    sfdc_writes JSONB,           -- [{object, field, old_value, new_value, timestamp}]
    slack_message_ts TEXT,
    rep_action TEXT,             -- "push"|"edit"|"skip"|"snooze"|"auto_push"|null
    rep_action_at TIMESTAMPTZ,
    status TEXT,                 -- "extracted"|"pending_review"|"pushed"|"skipped"|"failed"
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### Contact/Lead Deduplication

Before creating any Contact or Lead:

1. **Email exact match** — search SFDC Contacts + Leads by email
2. **Domain match** — extract domain, find Account by website/domain field
3. **Fuzzy name match** — same Account + similar name (Levenshtein distance ≤ 2) → flag as potential dupe, don't auto-create
4. **Alias handling** — if attendee email domain matches an existing Account's domain, associate to that Account even if the specific Contact doesn't exist
5. **Forwarded invites** — if attendee count on calendar invite differs from Fellow transcript speaker count, use transcript speakers as source of truth for who actually attended

### Opportunity Deduplication (Net New)

Before creating a new Lead from an unmatched meeting:

1. Check if another unmatched meeting from the same company domain was processed in the last 14 days
2. If yes → associate to the same Lead/Opp instead of creating a new one
3. If a Lead was created from a previous meeting and has since been converted → associate to the resulting Opp
4. Key: `company_domain + rep_id + 14d_window` → single Lead, multiple Activities

---

## SFDC Field Mapping Spec

### Object Model

| Data Type | SFDC Object | Rationale |
|-----------|-------------|-----------|
| Meeting summary + action items | **Task** (Activity) | Standard activity tracking, appears in Activity Timeline on Opp/Account/Contact |
| Extracted deal signals | **Opportunity** fields | Direct field updates for pipeline accuracy |
| New people discovered | **Lead** (net-new) or **Contact** (existing Account) | Lead-first for net-new; Contact if Account exists |
| Full extraction JSON | **Custom Object: Meeting_Sync__c** | Audit trail, replay capability, not visible to reps by default |

### Opportunity Field Mapping

| JSON Field | SFDC Object.Field | API Name | Write Rule | Format | Example |
|------------|-------------------|----------|------------|--------|---------|
| `summary` | Task.Description | `Description` | Always write (new Task per meeting) | Plain text, max 32k chars | "Customer evaluating SIP migration from Twilio. CTO attended..." |
| `action_items` | Task.Description (appended) | `Description` | Append to Task body under "Action Items" header | Bulleted list with owner + date | "• [Us] Send POC credentials — Mar 8\n• [Them] Internal security review — Mar 15" |
| `action_items[0]` (primary) | Opportunity.NextStep | `NextStep` | Fill if empty, or update if newer date | Free text, max 255 chars | "Send POC credentials by Mar 8" |
| `action_items[0].due_date` | Opportunity.Next_Step_Date__c | `Next_Step_Date__c` | Fill if empty, or update if newer | YYYY-MM-DD | 2026-03-08 |
| `competitors` | Opportunity.Competitors__c | `Competitors__c` | Append new values; semicolon-delimited; normalize to title case; max 255 chars; dedup before append | Semicolon-delimited | "Twilio; Vonage; Bandwidth" |
| `budget.mentioned` | Opportunity.MEDPICC_Budget__c | `MEDPICC_Budget__c` | Fill if empty only | Picklist or text | "Confirmed — Q3 budget approved" |
| `budget.signals` | Meeting_Sync__c.Budget_Signals__c | `Budget_Signals__c` | Always write (audit) | Long text | Raw extracted quotes |
| `authority.decision_maker` | Opportunity.MEDPICC_Authority__c | `MEDPICC_Authority__c` | Fill if empty only | Text | "Sarah Chen, CTO" |
| `authority.approval_chain` | Meeting_Sync__c.Authority_Notes__c | `Authority_Notes__c` | Always write (audit) | Long text | "CTO approves, needs CFO sign-off >$100k" |
| `timeline.target_date` | Opportunity.MEDPICC_Timeline__c | `MEDPICC_Timeline__c` | Fill if empty only | Text or Date | "Go-live target July 2026" |
| `pain_points` | Opportunity.MEDPICC_Pain__c | `MEDPICC_Pain__c` | Fill if empty only | Long text | "Current provider dropping 5% of calls in APAC" |
| `objections` | Meeting_Sync__c.Objections__c | `Objections__c` | Always write (audit) | Long text | "Concerned about porting timeline" |
| `sentiment` | Meeting_Sync__c.Sentiment__c | `Sentiment__c` | Always write (audit) | Picklist: positive/neutral/stalling/at_risk | "positive" |
| `stage_signal` | Meeting_Sync__c.Stage_Signal__c | `Stage_Signal__c` | Always write (audit). Never auto-update Opportunity.StageName. | Text | "Asked for contract — possible Negotiation" |
| `new_contacts` | Contact (or Lead) | — | See dedup rules above | — | — |
| `new_contacts[].role` | OpportunityContactRole.Role | `Role` | Add if not exists | Picklist | "Decision Maker" |

### Competitor Field Rules

- **Delimiter:** Semicolon + space (`; `)
- **Normalization:** Title case, trim whitespace, dedup
- **Max length:** 255 chars. If append would exceed, log overflow to Meeting_Sync__c and Slack-notify rep
- **Never remove** existing values. Append-only.
- **Canonical mapping:** Maintain a lookup table for common aliases (e.g., "AWS" = "Amazon Connect", "AMZN Connect" = "Amazon Connect")

### Task (Activity) Format

```
Subject: "[AutoSync] Meeting: {Company} — {Meeting Title}"
Due Date: {meeting_date}
Status: Completed
Priority: Normal
Description:
---
## Summary
{extracted_summary}

## Action Items
• [{side}] {action} — {owner}, {due_date}
• [{side}] {action} — {owner}, {due_date}

## Signals
- Competitors: {list}
- Budget: {signal}
- Timeline: {signal}
- Sentiment: {sentiment}

---
Synced by MeetingSync | {timestamp} | ID: {sync_id}
```

### SFDC Custom Objects Required

| Object | Purpose | Fields |
|--------|---------|--------|
| `Meeting_Sync__c` | Audit trail for every sync | `Fellow_Meeting_ID__c`, `Idempotency_Key__c`, `Extraction_JSON__c`, `Match_Confidence__c`, `Rep_Action__c`, `SFDC_Writes_JSON__c`, `Sync_Status__c`, `Created_Date__c` |

---

## Net-New: Lead-First Strategy

Auto-creating Account + Contact + Opportunity is too aggressive. Net-new meetings follow a Lead-first flow:

### Gating Rules

| Signal Count | Action |
|--------------|--------|
| 0-1 signals (just a meeting happened) | Create **Lead** with meeting Activity attached |
| 2-3 signals (use case + one of: budget/timeline/authority) | Create **Lead**, flag as "Sales Qualified" in Slack notification |
| 4+ signals (use case + budget + timeline + authority) | Suggest **Lead conversion** to rep (create Account + Contact + Opp). Still requires rep click. |

**Signals defined:**
- Use case identified
- Budget mentioned or confirmed
- Timeline stated
- Decision maker identified
- Volume/scale mentioned
- Active evaluation (comparing vendors)

### Lead Field Mapping

| JSON Field | Lead Field | API Name |
|------------|-----------|----------|
| `new_contacts[0].name` | Name | `FirstName`, `LastName` |
| `new_contacts[0].email` | Email | `Email` |
| `new_contacts[0].title` | Title | `Title` |
| Company (from domain/transcript) | Company | `Company` |
| `pain_points[0]` | Description | `Description` |
| `technical_requirements` | Product Interest | `Product_Interest__c` |
| Meeting source | Lead Source | `LeadSource` = "Meeting - Auto Captured" |
| Signal count | Rating | `Rating` = Hot/Warm/Cold based on count |

### Conversion Flow

When rep clicks "Convert to Opp" in Slack:
1. System calls SFDC Lead Convert API
2. Creates Account (or matches existing by domain)
3. Creates Contact from Lead
4. Creates Opportunity with all extracted fields pre-filled
5. Moves all Activities from Lead to new Opp

---

## Operations

### Retry Policy

| Integration | Retry Strategy | Max Retries | Backoff |
|-------------|---------------|-------------|---------|
| Fellow API (transcript fetch) | Retry on 429, 500, 502, 503, timeout | 5 | Exponential: 1s, 2s, 4s, 8s, 16s |
| SFDC API (read/match) | Retry on 500, 503, rate limit | 3 | Exponential: 2s, 4s, 8s |
| SFDC API (write) | Retry on 500, 503. **No retry on 400** (bad data). | 3 | Exponential: 2s, 4s, 8s |
| Slack API (notification) | Retry on 429, 500 | 3 | Respect `Retry-After` header |
| Google Calendar API | Retry on 429, 500, 503 | 3 | Exponential: 1s, 2s, 4s |
| AI Extraction (Claude) | Retry on 529 (overloaded), timeout | 2 | 5s, 15s |

### Dead Letter Queue

Failed syncs after max retries go to a DLQ:

```sql
CREATE TABLE sync_dlq (
    id UUID PRIMARY KEY,
    sync_ledger_id UUID REFERENCES sync_ledger(id),
    failure_stage TEXT,          -- "transcript_fetch"|"extraction"|"match"|"sfdc_write"|"slack_notify"
    error_message TEXT,
    error_code TEXT,
    retry_count INT,
    payload JSONB,
    created_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution TEXT              -- "auto_retry"|"manual_fix"|"skipped"
);
```

**DLQ Replay:** Admin CLI command to replay failed syncs:
```bash
meeting-sync dlq list --status unresolved
meeting-sync dlq replay --id <uuid>
meeting-sync dlq replay --stage sfdc_write --since 2026-02-25
```

### Monitoring Dashboard

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Extraction accuracy (rep edit rate) | Slack interaction logs | >30% edit rate sustained over 1 week |
| Match confidence distribution | sync_ledger | >20% low-confidence matches |
| Push latency (meeting end → SFDC write) | sync_ledger timestamps | p95 > 4 hours |
| SFDC write failure rate | sync_dlq | >5% failure rate over 24h |
| Slack response rate | Slack interaction logs | <50% response rate over 1 week |
| DLQ depth | sync_dlq | >20 unresolved items |
| Fellow API availability | Health check | Any downtime > 15 min |
| Transcript fetch success rate | sync_ledger | <95% success |
| Meetings processed per day | sync_ledger | Drop >50% from trailing 7d average |

### Polling Interval (Pre-Webhook)

- **L1-L3:** Cron every 30 minutes during business hours (6am-9pm per rep timezone)
- **Off-hours:** Every 2 hours (catch late meetings, timezone spread)
- **Cost:** ~48 Fellow API calls/day per org, well within rate limits
- **Target:** Move to event-driven (Fellow webhook or GCal push notification) at L4

---

## Security and Permissions

### Slack Visibility Matrix

| Content | Rep (deal owner) | Rep (non-owner) | Manager | Admin |
|---------|-----------------|-----------------|---------|-------|
| Meeting summary | ✅ | ❌ | ✅ (their team only) | ✅ |
| Extracted fields | ✅ | ❌ | ✅ (their team only) | ✅ |
| Raw transcript link | ✅ | ❌ | ❌ | ✅ |
| Pricing/discount mentions | ✅ (flagged as sensitive) | ❌ | ✅ (flagged) | ✅ |
| Competitor intel | ✅ | ❌ | ✅ | ✅ |
| Manager digest (aggregate) | ❌ | ❌ | ✅ (their team) | ✅ |

### Data Handling

- Raw transcripts **never** stored in SFDC — only structured extractions and summaries
- Extraction payloads stored in `Meeting_Sync__c` (SFDC) with same visibility as the parent Opportunity
- Slack messages sent as ephemeral DMs to deal owner only (not channels)
- Manager digest contains aggregate stats only, not individual meeting content
- Pricing/discount amounts detected in transcripts are flagged `[SENSITIVE]` in Slack summary
- sync_ledger and sync_dlq follow standard data retention (90 days, then archive)

### SFDC Permissions

- Integration user: dedicated service account with API-only profile
- Object access: Task (create), Opportunity (read + update specific fields), Contact (read + create), Lead (read + create + convert), Meeting_Sync__c (full CRUD)
- Field-level security: integration user can only write to mapped fields listed above
- No delete permissions on any object

---

## Human-in-the-Loop UX (Detailed)

### Slack Message: Matched Opportunity

```
📋 Meeting Synced | Feb 26, 2026

🏢 Acme Corp — "Q3 Migration Planning"
👤 @jane.doe
🔗 Acme Corp - SIP Trunking (Stage: Discovery) [View in SFDC →]
📊 Match confidence: High

━━━ Summary ━━━
Customer evaluating SIP trunking migration from Twilio.
CTO Sarah Chen attended with VP Eng. Budget approved for
Q3, targeting July go-live. Need POC environment by Mar 15.

━━━ Updates to push ━━━
  Field                 Value                    Currently
  Next Step             Send POC credentials     (empty)
  Next Step Date        2026-03-08               (empty)
  Competitors           + Twilio                 (empty)
  Budget                Confirmed — Q3           (empty)
  Decision Maker        Sarah Chen, CTO          (empty)
  Timeline              Go-live July 2026        (empty)

━━━ Action Items ━━━
  • [Us] Send POC credentials — Jane, Mar 8
  • [Them] Internal security review — Mar 15
  • [Us] Follow up on number porting reqs — Jane, Mar 10

━━━━━━━━━━━━━━━━━━

[✅ Push All]  [✏️ Edit]  [⏰ Snooze 4h]  [❌ Skip]
```

### Button Behaviors

| Button | Action |
|--------|--------|
| **✅ Push All** | Writes all listed fields to SFDC. Creates Task with summary + action items. Adds Contact Roles. Confirms with ✅ reaction. |
| **✏️ Edit** | Opens Slack modal with editable fields (pre-filled with extracted values). Each field has a checkbox to include/exclude. Rep modifies and clicks "Push Selected." |
| **⏰ Snooze 4h** | Re-sends the notification in 4 hours. Tracks snooze count. After 2 snoozes, auto-pushes safe fields only (Task + summary). |
| **❌ Skip** | Logs skip reason (optional dropdown: "Not relevant" / "Already updated" / "Wrong match" / "Other"). No SFDC write. |

### Edit Modal Fields

```
┌─────────────────────────────────────┐
│ Edit Meeting Sync — Acme Corp       │
│                                     │
│ ☑ Summary                          │
│ [editable text area]                │
│                                     │
│ ☑ Next Step                        │
│ [Send POC credentials_____________] │
│                                     │
│ ☑ Next Step Date                   │
│ [2026-03-08]                        │
│                                     │
│ ☑ Competitors                      │
│ [Twilio__________________________ ] │
│                                     │
│ ☐ Budget (uncheck to skip)         │
│ [Confirmed — Q3]                    │
│                                     │
│ ☑ Decision Maker                   │
│ [Sarah Chen, CTO]                   │
│                                     │
│         [Push Selected]  [Cancel]   │
└─────────────────────────────────────┘
```

### Slack Message: Net New (No Match)

```
📋 New Meeting Captured | Feb 26, 2026

🏢 Unknown — "Intro Call: GlobalTech Inc"
👤 @john.smith
🔗 No SFDC match found
📊 Signals: 3/6 (Use case ✓ Budget ✓ Timeline ✓)

━━━ Summary ━━━
Inbound interest in programmable voice APIs. Currently on
RingCentral, 50k minutes/month. Evaluating 3 vendors.
VP Product Mike Torres driving evaluation, Q2 decision.

━━━ Suggested Lead ━━━
  Name          Mike Torres
  Title         VP Product
  Email         mike.torres@globaltech.com
  Company       GlobalTech Inc
  Rating        🔥 Hot (3 signals)
  Product       Voice API
  Source        Meeting - Auto Captured

━━━━━━━━━━━━━━━━━━

[🆕 Create Lead]  [🔗 Link to Existing]  [⏰ Snooze]  [❌ Skip]
```

| Button | Action |
|--------|--------|
| **🆕 Create Lead** | Creates Lead with pre-filled fields. Attaches meeting Activity. If 4+ signals, prompts "Convert to Opportunity now?" |
| **🔗 Link to Existing** | Opens search modal. Rep types Account/Opp name. Typeahead search. Select → associate meeting as Activity on that record. |
| **⏰ Snooze** | Same as matched flow |
| **❌ Skip** | Same as matched flow |

### Confirm Match Flow (Low Confidence)

When match confidence is medium:

```
📋 Meeting Synced | Feb 26, 2026

🏢 Possible match — "Call with Beta Systems"
👤 @jane.doe

I found 2 possible matches:

1. Beta Systems Inc — Enterprise Voice (Stage: Negotiation)
   Last activity: Feb 20 | Owner: @jane.doe
   
2. Beta Systems Ltd — SMS Platform (Stage: Discovery)  
   Last activity: Jan 15 | Owner: @mike.chen

[1️⃣ Match #1]  [2️⃣ Match #2]  [🆕 New Lead]  [❌ Skip]
```

One click. No scavenger hunt.

---

## LADDER (Build)

### L1 — Foundation (Week 1)

**Goal:** Prove extraction quality. Zero SFDC writes.

**Deliverables:**
- Transcript-source abstraction layer (Fellow adapter first, interface supports swap)
- Fellow API integration: pull transcripts for completed meetings (org-wide)
- AI extraction pipeline: transcript → structured JSON per schema above
- SFDC match logic with confidence scoring
- Slack output: post extracted summary to rep's DM (read-only, no buttons)
- sync_ledger table and idempotency key implementation
- Contact dedup logic (email + domain + fuzzy name)

**Acceptable Polling Interval:** Every 30 minutes during business hours.

**Success Criteria:** Reps confirm >80% extraction accuracy across 20+ meetings.

---

### L2 — Human-in-the-Loop Writes (Weeks 2-3)

**Goal:** SFDC writes with rep approval via Slack.

**Deliverables:**
- Interactive Slack messages with Push/Edit/Snooze/Skip buttons (see UX spec above)
- Edit modal with per-field checkboxes
- Confirm-match flow for low-confidence matches
- SFDC write operations per field mapping spec
- Meeting_Sync__c custom object deployed
- All auto-updates tagged `[AutoSync]`
- DLQ for failed writes
- Net-new Lead creation flow (Lead-first, not Opp-first)

**SFDC Write Rules:**
- Never auto-downgrade Opportunity stage
- Never overwrite existing field values — append or fill empty only
- Stage upgrades surfaced as suggestion in Slack, never auto-applied

**Success Criteria:** >70% rep response rate. <10% error rate on pushed data.

---

### L3 — Auto-Push + Accountability (Weeks 4-5)

**Goal:** Remove friction for high-confidence matches. Manager visibility.

**Deliverables:**
- Auto-push after 24h for matched Opps, **constrained to safe writes only:**
  - ✅ Task/Activity creation (summary + action items)
  - ✅ Next Step + Next Step Date (if empty)
  - ❌ No MEDPICC field writes unless confidence ≥ 90% AND field is empty
  - ❌ No stage changes ever without rep confirmation
- Auto-create Lead for net-new (not Opp) with meeting Activity
- Lead auto-conversion prompt when signal count reaches 4+
- Snooze tracking (2 snoozes → auto-push safe fields)
- Manager weekly digest with team stats
- Monitoring dashboard (extraction accuracy, match confidence, push latency, failure rate)
- DLQ replay tooling

**Success Criteria:** 95%+ of external meetings have SFDC activity logged. Manager adoption of weekly report.

---

### L4 — Full Automation + Intelligence (Weeks 6+)

**Goal:** System runs autonomously. Event-driven. Adds predictive value.

**Deliverables:**
- Event-driven trigger (Fellow webhook or GCal push notification) replaces cron
- Multi-meeting signal accumulation per Opportunity (trend sentiment, track MEDPICC progress)
- Deal health scoring from sentiment trends
- Cross-rep intelligence: "3 reps heard [Competitor] mentioned this month"
- Forecast confidence scoring: opps with rich auto-synced data vs. sparse manual entries
- Transcript source swap capability tested (at least one alternative adapter)

---

## Match Logic (Priority Order)

| Priority | Method | Confidence |
|----------|--------|------------|
| 1 | External attendee email → SFDC Contact → Account → most recent open Opp | High |
| 2 | Calendar invite has SFDC link in description | High |
| 3 | Meeting title contains Account name → open Opp on that Account | Medium |
| 4 | Company domain from attendee email → Account website match | Medium |
| 5 | No match | — |

If confidence < 80%: Slack asks rep to confirm match (see low-confidence UX above).

---

## Escalation Matrix

| Scenario | Action |
|----------|--------|
| Match found, high confidence | Slack with push/edit/snooze/skip |
| Match found, low confidence | Slack with "confirm match" multi-option |
| No match, company exists in SFDC | Slack with "Link to existing" prominent |
| No match, company not in SFDC | Slack with "Create Lead" prominent |
| Internal meeting (no external attendees) | Skip entirely, no notification |
| Rep doesn't respond in 24h (L3+) | Auto-push safe fields only |
| Rep snoozes twice (L3+) | Auto-push safe fields only |

---

## Stack

| Component | Tool | Notes |
|-----------|------|-------|
| Transcripts | Fellow API (org-wide) | Behind abstraction layer; swappable |
| Meeting context | Google Calendar API | Attendees, title, description |
| Extraction | Claude (structured output) | JSON mode, schema-constrained |
| CRM writes | Salesforce API | Dedicated integration user |
| Notifications | Slack (Block Kit interactive messages) | Modals for edit flow |
| Orchestration | Cron (L1-L3), webhooks (L4) | 30-min polling during business hours |
| Storage | PostgreSQL | sync_ledger, sync_dlq |
| Monitoring | Internal dashboard | Metrics per ops table above |
| Audit | SFDC Meeting_Sync__c + `[AutoSync]` tags | Full write history |

---

## Dependencies

| Dependency | Owner | Status | Blocker? |
|------------|-------|--------|----------|
| Fellow org-wide API access | IT/RevOps | TBD | Yes — L1 blocker |
| SFDC custom fields (MEDPICC) exist on Opportunity | RevOps/SFDC Admin | TBD | L2 blocker |
| SFDC custom object: Meeting_Sync__c | RevOps/SFDC Admin | TBD | L2 blocker |
| SFDC integration user (API-only) | SFDC Admin | TBD | L2 blocker |
| Slack app with interactive message permissions | IT | TBD | L2 blocker |
| Google Calendar API (org-wide read) | IT | TBD | L1 blocker |
| Competitor alias lookup table | RevOps | TBD | Nice-to-have for L2 |

---

## Implementation Plan

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    meeting-sync service                    │
│                  (Python / FastAPI)                        │
│                                                           │
│  ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐ │
│  │ Ingest  │→ │ Extract   │→ │ Match   │→ │ Notify   │ │
│  │ Worker  │  │ Worker    │  │ Engine  │  │ Worker   │ │
│  └────┬────┘  └─────┬─────┘  └────┬────┘  └────┬─────┘ │
│       │             │              │             │        │
│  Fellow API    Claude API     SFDC API      Slack API    │
│  GCal API                                                │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              PostgreSQL                           │    │
│  │  sync_ledger · sync_dlq · competitor_aliases     │    │
│  │  meeting_cache · config                          │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Service runtime** | Python 3.12 + FastAPI | Team fluency, async-native, rapid iteration |
| **Task orchestration** | Celery + Redis | Retry logic, DLQ, scheduling, rate limiting out of the box |
| **Database** | PostgreSQL 16 | sync_ledger, DLQ, config. Telnyx standard. |
| **Cache / Broker** | Redis 7 | Celery broker + idempotency key cache (TTL 7d) |
| **AI Extraction** | Claude API (claude-sonnet-4-20250514) | Structured JSON output, cost-effective for extraction. Upgrade to Opus if accuracy insufficient. |
| **Containerization** | Docker | Standard Telnyx deployment unit |
| **Orchestration** | Kubernetes (Telnyx infra) | Existing cluster, ArgoCD for deploys |
| **CI/CD** | GitHub Actions → ArgoCD | Standard Telnyx pipeline |
| **Monitoring** | Prometheus + Grafana | Telnyx standard. Custom dashboard for sync metrics. |
| **Alerting** | Alertmanager → Slack | Telnyx standard |
| **Secrets** | Vault | API keys for Fellow, SFDC, Slack, GCal, Claude |

### External APIs Required

| API | Auth Method | Rate Limits | Cost |
|-----|------------|-------------|------|
| **Fellow API** | OAuth2 (org-wide service account) | TBD — need to confirm with Fellow | Included in Fellow subscription |
| **Salesforce REST API** | OAuth2 (Connected App, JWT bearer flow) | 100k calls/day (Enterprise) | Included in SFDC license |
| **Slack Web API** | Bot token (OAuth2) | Tier 2-3 (20-50 req/min per method) | Free |
| **Google Calendar API** | OAuth2 (service account with domain-wide delegation) | 1M queries/day | Free |
| **Claude API** | API key | Per-token pricing | ~$0.01-0.03 per meeting extraction |

### Service Components

#### 1. Ingest Worker
```
Trigger: Cron (every 30 min) or Fellow webhook (L4)
Input:   Fellow API → completed meetings since last poll
Output:  Raw transcript + attendee list + metadata → meeting_cache table
Logic:
  - Fetch meetings completed since last sync_point
  - Filter: skip if all attendees are @telnyx.com (internal)
  - Filter: skip if meeting < 5 min (accidental joins)
  - Dedup: check idempotency_key in sync_ledger
  - Enqueue extraction task
```

#### 2. Extract Worker
```
Trigger: Celery task from Ingest Worker
Input:   Raw transcript + meeting metadata
Output:  Structured JSON per extraction schema → sync_ledger
Logic:
  - Build prompt: system instructions + schema + transcript
  - Call Claude API with JSON mode
  - Validate response against schema (Pydantic)
  - If validation fails: retry with error feedback (1x), then DLQ
  - Store extraction in sync_ledger
  - Enqueue match task
```

**Prompt Strategy:**
- System prompt: role, rules, schema definition, examples
- User prompt: transcript + attendee list + meeting title
- Temperature: 0 (deterministic extraction)
- Max tokens: 4096 (sufficient for schema)
- Model: claude-sonnet-4-20250514 (cost-effective). Fallback: claude-opus-4-20250514 if accuracy <80%

#### 3. Match Engine
```
Trigger: Celery task from Extract Worker
Input:   Extraction JSON + attendee emails
Output:  Match result (opp_id + confidence) or no_match → sync_ledger
Logic:
  - Priority 1: attendee email → SFDC Contact → Account → open Opp
  - Priority 2: calendar description contains SFDC URL → direct match
  - Priority 3: meeting title → Account name fuzzy match → open Opp
  - Priority 4: attendee email domain → Account website match
  - Score confidence (high/medium/low)
  - Contact dedup check before any create
  - Opp dedup check (same domain + rep + 14d window)
  - Enqueue notify task
```

#### 4. Notify Worker
```
Trigger: Celery task from Match Engine
Input:   Extraction + match result
Output:  Slack interactive message → rep DM
Logic:
  - Build Block Kit message per UX spec
  - Post to rep's Slack DM (lookup rep by Opp owner email → Slack user ID)
  - Store slack_message_ts in sync_ledger
  - If Slack post fails: retry per policy, then DLQ
  - Listen for button interactions via Slack Events API
```

#### 5. SFDC Writer
```
Trigger: Slack button interaction OR 24h auto-push timer (L3)
Input:   Approved extraction + match result + any rep edits
Output:  SFDC API calls → created/updated records
Logic:
  - Read current field values from SFDC (for append/fill-if-empty logic)
  - Build write set per field mapping spec
  - Execute writes in order: Contact/Lead → ContactRole → Task → Opp fields
  - Tag all writes with [AutoSync] + sync_id
  - Log all writes (old_value → new_value) to sync_ledger.sfdc_writes
  - If any write fails: retry per policy, partial success logged, DLQ for failures
  - Post confirmation reaction (✅) on Slack message
```

#### 6. Scheduler / Timer
```
Trigger: Celery Beat
Jobs:
  - Every 30 min (business hours): trigger Ingest Worker
  - Every 2 hours (off-hours): trigger Ingest Worker
  - Every 1 hour: check for pending reviews > 24h → auto-push safe fields (L3)
  - Every 1 hour: check for snoozed messages past snooze time → re-notify
  - Monday 9am per timezone: generate manager weekly digest
  - Daily 2am UTC: DLQ health check → alert if depth > 20
```

### Infrastructure

#### Kubernetes Resources

```yaml
# meeting-sync deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meeting-sync-api
  namespace: meeting-sync
spec:
  replicas: 2
  # FastAPI server: Slack webhook receiver + admin API
  resources:
    requests: { cpu: 250m, memory: 256Mi }
    limits: { cpu: 500m, memory: 512Mi }

---
# Celery workers
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meeting-sync-worker
  namespace: meeting-sync
spec:
  replicas: 3  # ingest + extract + notify/write parallelism
  resources:
    requests: { cpu: 500m, memory: 512Mi }
    limits: { cpu: 1000m, memory: 1Gi }

---
# Celery Beat (singleton)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meeting-sync-beat
  namespace: meeting-sync
spec:
  replicas: 1
  resources:
    requests: { cpu: 100m, memory: 128Mi }
    limits: { cpu: 200m, memory: 256Mi }

---
# Redis
# Use existing Telnyx Redis cluster or deploy dedicated instance
# Dedicated preferred for isolation (Celery broker + result backend)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meeting-sync-redis
spec:
  replicas: 1
  resources:
    requests: { cpu: 100m, memory: 256Mi }
    limits: { cpu: 200m, memory: 512Mi }
```

#### Database

- **Cluster:** pgbot-main-18 (Telnyx standard) or dedicated if volume warrants
- **Database:** `meeting_sync`
- **Tables:** `sync_ledger`, `sync_dlq`, `competitor_aliases`, `meeting_cache`, `config`
- **Migrations:** Alembic
- **Backup:** Standard Telnyx PG backup policy (daily snapshots, WAL archiving)

#### Networking

- FastAPI service: internal ClusterIP (no external exposure needed)
- Slack Events API: route through existing Telnyx Slack app's webhook endpoint, or dedicated ingress with `/slack/events` path
- All external API calls (Fellow, SFDC, Claude, GCal) egress through standard NAT gateway

### Deployment Plan

#### Pre-Deployment (Week 0)

| Task | Owner | Duration |
|------|-------|----------|
| Fellow API: request org-wide OAuth credentials | IT/RevOps | 1-2 days |
| Fellow API: confirm webhook availability and schema | Engineering | 1 day |
| SFDC: create Connected App (JWT bearer flow) | SFDC Admin | 1 day |
| SFDC: create integration user (API-only profile) | SFDC Admin | 1 day |
| SFDC: create Meeting_Sync__c custom object + fields | RevOps/SFDC Admin | 2-3 days |
| SFDC: confirm MEDPICC fields exist on Opportunity | RevOps | 1 day |
| SFDC: field-level security for integration user | SFDC Admin | 1 day |
| Slack: create/configure app with interactive messages + events | IT | 1 day |
| GCal: service account with domain-wide delegation | IT | 1 day |
| Claude API: provision key, set budget alert | Engineering | 1 hour |
| Vault: provision secrets for all APIs | Platform | 1 day |
| K8s: create namespace, RBAC, resource quotas | Platform | 1 day |
| PG: create database + roles | Platform (use database-creation skill) | 1 day |
| Grafana: create dashboard shell | Engineering | 1 day |

**Estimated pre-deployment:** 1 week (mostly waiting on admin tasks, parallelizable)

#### L1 Deployment (Week 1)

| Day | Milestone |
|-----|-----------|
| Mon | Repo scaffolded (Python template), CI pipeline, Docker build |
| Mon | Transcript source abstraction layer + Fellow adapter |
| Tue | Ingest Worker: Fellow polling + internal meeting filter + dedup |
| Tue | Extract Worker: Claude prompt + Pydantic validation |
| Wed | Match Engine: SFDC query logic + confidence scoring |
| Wed | Contact dedup logic |
| Thu | Notify Worker: read-only Slack DM (no buttons) |
| Thu | sync_ledger + idempotency implementation |
| Fri | E2E test with 20 real transcripts. Deploy to dev. |
| Fri | Deploy to prod (read-only mode). Monitor over weekend. |

#### L2 Deployment (Weeks 2-3)

| Week | Milestone |
|------|-----------|
| W2 Mon-Tue | Slack interactive messages (Block Kit) + button handlers |
| W2 Wed | Edit modal + per-field checkboxes |
| W2 Thu | SFDC Writer: Task creation + safe field updates |
| W2 Fri | Confirm-match flow for low-confidence. Deploy to dev. |
| W3 Mon-Tue | Net-new Lead creation flow + Lead dedup |
| W3 Wed | DLQ implementation + replay CLI |
| W3 Thu | Monitoring dashboard (Grafana) + Alertmanager rules |
| W3 Fri | E2E test full flow. Deploy to prod. |

#### L3 Deployment (Weeks 4-5)

| Week | Milestone |
|------|-----------|
| W4 Mon-Tue | Auto-push timer (24h, safe fields only) |
| W4 Wed | Snooze logic (re-notify + 2-snooze auto-push) |
| W4 Thu-Fri | Manager weekly digest. Deploy to dev. |
| W5 Mon-Tue | Lead conversion prompt (4+ signals) |
| W5 Wed | Opp dedup (same domain + rep + 14d window) |
| W5 Thu-Fri | Load test, prod deploy, monitor first full week |

#### L4 Deployment (Weeks 6+)

| Milestone | Trigger |
|-----------|---------|
| Fellow webhook integration | When webhook access confirmed |
| Multi-meeting signal accumulation | After 4+ weeks of data |
| Deal health scoring | After signal accumulation baseline |
| Cross-rep competitor intelligence | After 100+ meetings processed |
| Forecast confidence scoring | After pipeline data completeness >80% |

### Cost Estimate

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| K8s compute (API + workers + beat) | ~$50-80 | Shared cluster, minimal resources |
| Redis | ~$20 | Small dedicated instance |
| PostgreSQL | ~$0 | Existing Telnyx PG cluster |
| Claude API (extraction) | ~$50-150 | ~100-500 meetings/month × $0.01-0.03/extraction |
| Fellow API | $0 | Included in subscription |
| SFDC API | $0 | Included in license |
| Slack API | $0 | Free |
| GCal API | $0 | Free |
| **Total** | **~$70-230/month** | Scales linearly with meeting volume |

### Repo Structure

```
meeting-sync/
├── Dockerfile
├── docker-compose.yml          # Local dev
├── pyproject.toml
├── alembic/                    # DB migrations
│   └── versions/
├── src/
│   ├── main.py                 # FastAPI app (Slack webhooks, admin API)
│   ├── config.py               # Settings (Pydantic BaseSettings)
│   ├── models.py               # SQLAlchemy models
│   ├── schema.py               # Pydantic schemas (extraction, match, etc.)
│   ├── workers/
│   │   ├── ingest.py           # Fellow polling + filtering
│   │   ├── extract.py          # Claude extraction + validation
│   │   ├── match.py            # SFDC matching + dedup
│   │   ├── notify.py           # Slack message builder + sender
│   │   ├── writer.py           # SFDC write operations
│   │   └── scheduler.py        # Celery Beat config
│   ├── integrations/
│   │   ├── transcript.py       # Abstract transcript source
│   │   ├── fellow.py           # Fellow API adapter
│   │   ├── salesforce.py       # SFDC read/write client
│   │   ├── slack.py            # Slack Block Kit builder + interactions
│   │   ├── calendar.py         # GCal client
│   │   └── claude.py           # Extraction prompt + API client
│   ├── services/
│   │   ├── dedup.py            # Contact/Lead/Opp dedup logic
│   │   ├── confidence.py       # Match confidence scoring
│   │   └── field_mapper.py     # JSON → SFDC field mapping + write rules
│   └── cli/
│       ├── dlq.py              # DLQ list/replay commands
│       └── backfill.py         # Historical transcript processing
├── tests/
│   ├── fixtures/               # Sample transcripts + SFDC responses
│   ├── test_extract.py
│   ├── test_match.py
│   ├── test_dedup.py
│   ├── test_writer.py
│   └── test_e2e.py
├── k8s/
│   ├── base/
│   │   ├── deployment-api.yaml
│   │   ├── deployment-worker.yaml
│   │   ├── deployment-beat.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── overlays/
│       ├── dev/
│       └── prod/
├── grafana/
│   └── dashboard.json
└── docs/
    ├── runbook.md              # Ops runbook
    └── field-mapping.md        # SFDC field reference
```

### Team / Ownership

| Role | Who | Responsibility |
|------|-----|----------------|
| **Product Owner** | Ian / RevOps lead | Requirements, field mapping approval, rollout decisions |
| **Engineering Lead** | TBD | Architecture, implementation, code review |
| **Backend Engineer(s)** | TBD (1-2) | Build workers, integrations, tests |
| **SFDC Admin** | RevOps | Custom objects, fields, integration user, field-level security |
| **IT** | IT | Fellow API access, GCal delegation, Slack app |
| **Platform** | Platform team | K8s namespace, PG database, Vault secrets |
| **QA / Pilot Reps** | 3-5 reps | Validate extraction quality during L1, test UX during L2 |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| % meetings with SFDC activity logged | 95%+ | SFDC report: meetings (calendar) vs activities |
| Time from meeting end to SFDC update | < 2 hours (cron), < 15 min (webhook) | sync_ledger timestamps |
| Rep response rate (Slack) | >70% within 24h | Slack interaction logs |
| Rep edit/override rate | Decreasing over time (target <15% by L3) | Slack interaction logs |
| Pipeline data completeness (next steps filled) | 90%+ | SFDC field population report |
| Match accuracy | >90% | Manual audit sample monthly |
| Lead junk rate (auto-created then junked) | <20% | SFDC Lead status report |
| DLQ depth | <10 unresolved at any time | sync_dlq monitoring |
| Extraction accuracy | >85% field-level accuracy | Rep edit rate as proxy + monthly audit |
