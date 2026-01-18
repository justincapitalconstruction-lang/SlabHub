# PRE-PHASE 0 BASELINE CONTRACT (NON-NEGOTIABLE)

This document is the authoritative governance contract for SlabHub stabilization.
Any agent (human or AI) making changes to this repository MUST comply with all rules below.

## 1. Purpose
SlabHub is undergoing phased stabilization to reach demo-ready reliability.
No work may occur unless governance, logging, restore points, and D:\ drive enforcement are respected.

## 2. Hard Rules (MUST / NEVER)
1. The ONLY allowed root is: `D:\SlabHub`
2. The system MUST NOT write to `C:\` under any circumstances.
3. Agents MUST NOT change working directories during execution.
4. Every agent session MUST:
   - Create a restore point BEFORE any code change (Git tag required)
   - Bump version by **+0.01** per session (only once per session)
   - Log intent BEFORE coding
   - Log results AFTER coding
5. No new features may be introduced until Phase 4 is completed and verified.
6. Silent failures are forbidden:
   - NO bare `except:`
   - NO swallowed exceptions
   - All errors must be recorded (logs + job_events where applicable)
7. If any requirement is unclear, work MUST STOP until clarified.

## 3. Scope Lock (Out of Scope Until Demo-Stable)
- GUI redesign / styling / button theme changes
- Performance optimizations not required for correctness
- Queue scaling / distributed systems work beyond demo needs
- Cloud deployment, auto-scaling, multi-region work
- Any "nice to have" features unrelated to core demo success

## 4. Demo-Stable Definition (Minimum Outcomes)
The system is demo-stable only when:
- Slabs can be added manually (admin UI) and saved reliably
- Slab images upload, store under `D:\SlabHub\data\...`, and render in admin + kiosk
- Metadata import (CSV/XLSX) works with visible error reporting
- Bulk selection + bulk operations work (minimum: tag/location/analyze)
- AI analysis runs repeatably with traceability:
  - request stored
  - response stored
  - result stored
  - failures visible and retryable
- Kiosk lists slabs, filters/searches, displays details + images

## 5. Required Reading (In Order)
Agents MUST read ALL of the following before any work:
1. `README.md`
2. `PRE_PHASE0_BASELINE.md` (this document)
3. `AGENTS_RULES_OF_ENGAGEMENT.md`
4. `PHASE_EXECUTION_PLAN.md`
5. `stability_maturity_checklist.md`
6. `SlabHub_FixPlan.md`
7. Deployment / schema documentation (if present in /docs)

## 6. Acknowledgement
By making any code change, the agent confirms:
- they read all required documents,
- they accept all hard rules,
- they will not proceed without restore points + version bump + logging,
- violations invalidate the work and may result in removal from the project.
