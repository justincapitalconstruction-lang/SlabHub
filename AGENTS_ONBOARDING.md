# SlabHub Agent Onboarding Guide

This document provides essential information for developers, AI agents, and operators working on the SlabHub project.

## Critical: Drive Policy

**NEVER write to C:\ drive. All SlabHub operations MUST use D:\ drive.**

This is enforced at multiple levels:
- Configuration validators in `config.py`
- Startup validation in `main.py`
- Service startup validation in `start_services.py`

See [DRIVE_POLICY.md](DRIVE_POLICY.md) for full details.

## Project Location

| Item | Path |
|------|------|
| Project Root | `D:\slabHub` |
| Database | `D:\slabHub\data\slabhub.db` |
| Labels | `D:\slabHub\data\labels\` |
| QR Codes | `D:\slabHub\data\qr\` |
| Logs | `D:\slabHub\data\logs\` |
| Backups | `D:\slabHub\data\backups\` |

**Note**: Documentation may reference `C:\SlabHub` in older sections - this is legacy and being updated. Always use `D:\slabHub`.

## Key Environment Variables

```env
# REQUIRED - Project root
SLABHUB_ROOT=D:/slabHub

# Database
DATABASE_URL=sqlite:///D:/slabHub/data/slabhub.db

# Server
PUBLIC_BASE_URL=http://localhost:8000
HOST=0.0.0.0
PORT=8000

# SlabCrop integration
SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output
```

## Version Information

Current version: **1.0.1** (see `VERSION` file)

Version is managed in two places (kept in sync):
- `VERSION` - Plain text file at project root
- `backend/app/version.py` - Python module

Use `scripts/bump_version.py` to update:
```bash
python scripts/bump_version.py patch   # 1.0.1 -> 1.0.2
python scripts/bump_version.py minor   # 1.0.1 -> 1.1.0
python scripts/bump_version.py major   # 1.0.1 -> 2.0.0
```

## Configuration Priority

Settings are loaded in this priority (highest to lowest):

1. Environment variables
2. `D:\slabHub\.env` file
3. Default values in `backend/app/config.py`

## Common Operations

### Starting the Server

**Option 1: Using start_services.py (Recommended)**
```bash
cd D:\slabHub
.venv-2\Scripts\activate
python scripts/start_services.py
```

**Option 2: Quick restart**
```bash
D:\slabHub\restart_server.bat
```

**Option 3: Direct uvicorn**
```bash
cd D:\slabHub
.venv-2\Scripts\activate
python -m uvicorn backend.app.main:app --reload
```

### Accessing the Application

| Interface | URL |
|-----------|-----|
| Kiosk (Public) | http://localhost:8000/kiosk |
| Admin | http://localhost:8000/admin |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### Database Operations

**Backup:**
```bash
python scripts/db_backup.py
```

**Restore:**
```bash
python scripts/db_restore.py --list
python scripts/db_restore.py <backup_file>
```

**Sanity Check:**
```bash
python scripts/db_sanity_check.py
```

## Before Making Changes

Always verify:

1. **Drive Policy**: All paths resolve to D:\ drive
2. **No hardcoded C:\ paths**: Search code for `C:/` or `C:\`
3. **Version updated**: Run `python scripts/bump_version.py` if needed
4. **Tests pass**: Run `pytest tests/`

## Code Structure

```
D:\slabHub\
├── backend\
│   └── app\
│       ├── config.py       # Settings and drive validators
│       ├── main.py         # FastAPI app, startup validation
│       ├── core\           # Core utilities
│       │   └── drive_validator.py  # Drive policy enforcement
│       ├── models\         # SQLAlchemy models
│       ├── routers\        # API routes
│       ├── services\       # Business logic
│       ├── templates\      # Jinja2 HTML templates
│       └── utils\          # Utilities (QR, labels, etc.)
├── scripts\                # Utility scripts
├── tests\                  # Test suite
├── data\                   # Application data (gitignored)
├── .env                    # Configuration
├── VERSION                 # Version number
├── DRIVE_POLICY.md         # Drive policy documentation
└── README.md               # Main documentation
```

## Validation Checklist

Before deploying changes:

- [ ] All paths use D:\ drive
- [ ] No new C:\ references added
- [ ] `SLABHUB_ROOT` is set in .env
- [ ] Application starts without drive policy errors
- [ ] Health endpoint returns correct version
- [ ] Tests pass

## Restore Points

Before making significant changes, create a restore point:

```bash
git tag restore/$(date +%Y-%m-%d)_before_change
```

Never delete restore points without project owner approval.

## Getting Help

- **Drive Policy Issues**: See [DRIVE_POLICY.md](DRIVE_POLICY.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Operations**: See [RUNBOOK.md](RUNBOOK.md)
- **Database**: See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
