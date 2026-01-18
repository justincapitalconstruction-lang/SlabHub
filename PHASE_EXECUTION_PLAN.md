# SLABHUB PHASE EXECUTION PLAN (DO NOT REORDER)

This file defines the allowed execution order.
No phase may begin until the previous phase is committed and verified.

## Phase 0 — Demo Lock + D:\ Enforcement
Goal: Ensure the system always runs from `D:\SlabHub` and never writes to `C:\`.
Actions:
- Enforce SLABHUB_ROOT = D:\SlabHub in .env and .env.example
- Ensure all storage folders are D:\SlabHub\data\...
- Disable watch folder by default
- Update README quickstart to ONLY D:\ paths
Verification:
- Startup logs show version + D:\ root + path map
- /health, /health/db, /health/storage return OK
Commit target: +0.01

## Phase 1 — Golden CRUD (Add Slab + Images)
Goal: Admin can add slab and images render in admin + kiosk.
Actions:
- Fix Add Slab workflow
- Fix image upload/storage/serve pipeline
Verification:
- Add slab appears in list
- Upload image renders in admin and kiosk
Commit target: +0.01

## Phase 2 — Metadata Import (CSV/XLSX)
Goal: Import metadata reliably with clear error reporting.
Actions:
- Fix import endpoint and logging
- Validate columns and produce summary
Verification:
- Import creates/updates slabs; errors captured
Commit target: +0.01

## Phase 3 — Multi-Select + Bulk Actions
Goal: Manage 750 slabs efficiently.
Actions:
- Add selection boxes + select all/none
- Add bulk tag/location/analyze trigger
Verification:
- Bulk action changes DB correctly
Commit target: +0.01

## Phase 4 — GPT Analysis Pipeline (Traceable + Repeatable)
Goal: Remove "no GPT analysis found" permanently.
Actions:
- Analyze action per slab and in bulk
- Persist request/response/results/errors
- Add retry and needs_review status
Verification:
- Analyze generates DB records and visible status
Commit target: +0.01

## Phase 5 — Catalog + Ground Truth Compare + Duplicate Detection
Goal: Demo-grade intelligence + repeatability.
Actions:
- Implement strict schema outputs + confidence
- Compare outputs to catalog truth
- Duplicate detection (hash first pass)
Verification:
- Analysis report shows confidence + duplicates
Commit target: +0.01

## Phase 6 — Kiosk Template Structure Match (Functional)
Goal: Match layout structure; styling later.
Actions:
- Ensure kiosk blocks align with template structure
- Confirm images and filtering work
Verification:
- Screenshot matches template structure
Commit target: +0.01

## Phase 7 — Demo Hardening + "Nothing Broke" Gate
Goal: Prevent regressions before demo.
Actions:
- Add demo smoke test script
- Lock stable-demo tag/branch
Verification:
- Smoke test passes
Commit target: +0.01
