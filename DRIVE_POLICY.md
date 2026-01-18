# SlabHub Drive Policy

## Overview

SlabHub enforces a strict drive policy to ensure data integrity, prevent accidental writes to system drives, and maintain consistent application behavior across all installations.

## Policy Rules

1. **All application code and data MUST reside on D:\ drive**
2. **Writing to C:\ drive is PROHIBITED**
3. **SLABHUB_ROOT must be set to D:\slabHub**

## Why This Policy Exists

- **Data Protection**: Separating application data from the system drive prevents accidental data loss during OS reinstalls or updates
- **Consistency**: Ensures all installations follow the same directory structure
- **Backup Simplicity**: All SlabHub data is in one predictable location
- **Security**: Reduces risk of system contamination from application files

## Environment Variable

The `SLABHUB_ROOT` environment variable defines the project root and is **required**:

```env
SLABHUB_ROOT=D:/slabHub
```

This variable is used to:
- Validate all configured paths at startup
- Resolve relative paths (e.g., `./data/labels`)
- Ensure all file operations stay within policy

## Validation

Drive policy is validated at multiple points:

### 1. Configuration Loading (config.py)
- Pydantic validators check all path fields
- Raises `ValueError` if C:\ path detected

### 2. Application Startup (main.py)
- `enforce_drive_policy_at_startup()` checks all settings
- Logs CRITICAL error and exits if violation detected

### 3. Service Startup (start_services.py)
- Drive validation runs before any services start
- Prevents server from starting with invalid configuration

## Violation Handling

If a drive policy violation is detected:

1. The application logs a **CRITICAL** error with details:
   ```
   DRIVE POLICY VIOLATION DETECTED
   SlabHub requires all data to reside on D:\ drive.
   The following paths violate this policy:
     - database_url: Writing to C:\ is prohibited... (current: sqlite:///C:/...)
   ```

2. The application terminates with **exit code 1**

3. The error message indicates which path violated the policy

## Configuration

All paths in `.env` should use D:\ drive:

```env
# Project Root (REQUIRED)
SLABHUB_ROOT=D:/slabHub

# Database
DATABASE_URL=sqlite:///D:/slabHub/data/slabhub.db

# SlabCrop Integration
SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output

# Relative paths (OK - resolved against SLABHUB_ROOT)
LABEL_OUTPUT_FOLDER=./data/labels
QR_OUTPUT_FOLDER=./data/qr
LOG_FILE=./data/logs/slabhub.log
```

## Relative Paths

Relative paths starting with `./` or `../` are **allowed** because they resolve relative to `SLABHUB_ROOT` (which is on D:\).

Examples of valid relative paths:
- `./data/labels` → `D:/slabHub/data/labels`
- `./data/qr` → `D:/slabHub/data/qr`
- `./data/logs/slabhub.log` → `D:/slabHub/data/logs/slabhub.log`

## Directory Structure

All SlabHub data should follow this structure on D:\:

```
D:\slabHub\                    # SLABHUB_ROOT
├── backend\                   # Application code
├── data\                      # All application data
│   ├── slabhub.db            # SQLite database
│   ├── labels\               # Generated label PDFs
│   ├── qr\                   # Generated QR code images
│   ├── logs\                 # Application logs
│   ├── archive\              # Processed images archive
│   └── backups\              # Database backups
├── scripts\                   # Utility scripts
├── .env                       # Configuration
└── VERSION                    # Version file
```

## Migration from C:\ to D:\

If migrating an existing installation from C:\ to D:\:

### Step 1: Stop Services
```bash
taskkill /IM python.exe /F
```

### Step 2: Copy Project
```bash
xcopy /E /I C:\SlabHub D:\slabHub
```

### Step 3: Update .env
Edit `D:\slabHub\.env`:
```env
SLABHUB_ROOT=D:/slabHub
DATABASE_URL=sqlite:///D:/slabHub/data/slabhub.db
```

### Step 4: Update Database Paths (if needed)
```bash
cd D:\slabHub
python scripts/normalize_db_paths.py --dry-run
python scripts/normalize_db_paths.py
```

### Step 5: Verify and Start
```bash
python scripts/start_services.py
```

Check for "Drive policy validation passed" in logs.

## Troubleshooting

### Error: "DRIVE POLICY VIOLATION DETECTED"

**Cause**: A configured path points to C:\ drive

**Solution**:
1. Check your `.env` file
2. Ensure `SLABHUB_ROOT=D:/slabHub`
3. Ensure `DATABASE_URL` uses D:\
4. Check any custom path configurations

### Error: "Path must be on D:\ drive"

**Cause**: Pydantic validator caught a C:\ path during config loading

**Solution**: Update the offending path in `.env` to use D:\

### Relative paths not resolving correctly

**Cause**: SLABHUB_ROOT not set or incorrect

**Solution**:
1. Ensure `SLABHUB_ROOT=D:/slabHub` is in `.env`
2. Restart the application

## See Also

- [DEPLOYMENT.md](DEPLOYMENT.md) - Installation guide
- [RUNBOOK.md](RUNBOOK.md) - Operations manual
- [AGENTS_ONBOARDING.md](AGENTS_ONBOARDING.md) - Developer onboarding
