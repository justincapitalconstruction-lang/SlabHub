# SlabHub Deployment Guide - Monday Launch

This guide provides comprehensive deployment instructions for the SlabHub Monday launch. Follow these steps carefully to ensure a smooth deployment.

## Table of Contents
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Environment Setup](#environment-setup)
- [Database Initialization](#database-initialization)
- [Service Configuration](#service-configuration)
- [Network Configuration](#network-configuration)
- [Testing Checklist](#testing-checklist)
- [Launch Day Procedures](#launch-day-procedures)
- [Troubleshooting](#troubleshooting)
- [Backup Procedures](#backup-procedures)
- [Rollback Plan](#rollback-plan)

---

## Pre-Deployment Checklist

### Hardware Requirements
- [ ] Windows 10/11 computer with minimum 8GB RAM
- [ ] 50GB available disk space (for images and database)
- [ ] Stable network connection (ethernet recommended)
- [ ] PM-241BT thermal printer (optional, for labels)
- [ ] USB cable or Bluetooth for printer connection
- [ ] Thermal labels (4x6 inch)
- [ ] Network switch/router for LAN access
- [ ] Mobile device(s) for QR code testing

### Software Requirements
- [ ] Python 3.10 or higher installed
- [ ] Git installed (optional, for version control)
- [ ] SlabCrop software installed and configured
- [ ] PM-241BT printer driver installed
- [ ] Windows Firewall configured
- [ ] Administrator access to Windows machine

### Pre-Deployment Tasks
- [ ] Backup any existing slab data
- [ ] Document current SlabCrop configuration
- [ ] Prepare JSON metadata file (if importing existing library)
- [ ] Test network connectivity between devices
- [ ] Verify printer functionality
- [ ] Create deployment folder: `C:\SlabHub`
- [ ] Note computer's IP address for network access

---

## Environment Setup

### Step 1: Install Python (if not already installed)

1. **Download Python 3.10+**
   - Visit: https://www.python.org/downloads/
   - Download Windows installer (64-bit recommended)

2. **Run Installer**
   - Check "Add Python to PATH"
   - Choose "Install Now"
   - Verify installation:
     ```bash
     python --version
     # Should show: Python 3.10.x or higher
     ```

### Step 2: Extract/Clone SlabHub

```bash
# Navigate to installation directory
cd C:\
mkdir SlabHub
cd SlabHub

# Extract files here or clone from repository
# Your project files should be in C:\SlabHub
```

### Step 3: Create Virtual Environment

```bash
# From C:\SlabHub directory
python -m venv venv
```

### Step 4: Activate Virtual Environment

```bash
# Activate the environment
venv\Scripts\activate

# Your prompt should now show (venv)
```

### Step 5: Install Dependencies

```bash
# Ensure you're in C:\SlabHub with (venv) active
pip install --upgrade pip
pip install -r requirements.txt
```

Verify installation:
```bash
pip list
# Should show fastapi, uvicorn, sqlalchemy, pillow, etc.
```

### Step 6: Configure Environment Variables

Create a `.env` file in `C:\SlabHub\`:

```env
# ============================================================================
# SlabHub Production Configuration
# ============================================================================

# Application Settings
# Replace 192.168.1.100 with your computer's actual IP address
PUBLIC_BASE_URL=http://192.168.1.100:8000
SECRET_KEY=your-secret-key-change-this-to-random-string
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/slabhub.db

# SlabCrop Integration
# Update this path to match your SlabCrop installation
SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output
SLABCROP_INBOX_FOLDER=./data/slabcrop_inbox
INCOMING_RAW_FOLDER=./data/incoming_raw
PROCESSED_ARCHIVE_FOLDER=./data/archive

# Watch Folder Service
ENABLE_WATCH_FOLDER=true

# Import Settings (optional - for initial import)
# IMPORT_METADATA_FILE=./data/imports/stone-identifications.json
# IMPORT_INPUT_FOLDER=./data/imports/images

# Image Processing
IMAGE_MIN_WIDTH=800
IMAGE_MIN_HEIGHT=800
DUPLICATE_THRESHOLD=10
MAX_IMAGE_SIZE_MB=10

# Label Generation (PM-241BT Printer)
LABEL_SIZE=4x6
LABEL_DPI=203
LABEL_OUTPUT_FOLDER=./data/labels

# QR Codes
QR_OUTPUT_FOLDER=./data/qr

# Logging
LOG_LEVEL=INFO
LOG_FILE=./data/logs/slabhub.log

# Feature Flags
ENABLE_AUTO_IMPORT=true
```

**CRITICAL CONFIGURATION NOTES:**

1. **PUBLIC_BASE_URL**:
   - Find your IP address: Run `ipconfig` in Command Prompt
   - Look for "IPv4 Address" under your active network adapter
   - Example: `192.168.1.100`
   - Update PUBLIC_BASE_URL to: `http://192.168.1.100:8000`
   - This URL will be embedded in QR codes

2. **SLABCROP_OUTPUT_FOLDER**:
   - Verify SlabCrop output folder location
   - Default is usually `D:/SlabCrop/output`
   - Must be an absolute path
   - Folder must exist before starting services

3. **SECRET_KEY**:
   - Generate a random string:
     ```python
     import secrets
     print(secrets.token_urlsafe(32))
     ```
   - Replace default value with generated key

### Step 7: Verify Configuration

```bash
# Test that configuration loads correctly
python -c "from backend.app.config import settings; print(f'Database: {settings.database_url}'); print(f'Public URL: {settings.public_base_url}')"
```

---

## Database Initialization

### Step 1: Create Data Directories

```bash
# From C:\SlabHub directory
mkdir data
mkdir data\logs
mkdir data\labels
mkdir data\qr
mkdir data\archive
mkdir data\imports
```

### Step 2: Initialize Database

```bash
# Ensure virtual environment is active
python scripts/init_db.py
```

Expected output:
```
Initializing database...
Database initialized successfully!
```

### Step 3: Verify Database Creation

```bash
# Check that database file was created
dir data\slabhub.db
```

You should see `slabhub.db` file in the `data` folder.

### Step 4: Import Existing Library (Optional)

If you have existing slab data to import:

```bash
# First, do a dry run to preview
python scripts/import_metadata.py --file data/imports/stone-identifications.json --dry-run

# If dry run looks good, do actual import
python scripts/import_metadata.py --file data/imports/stone-identifications.json
```

See [RUNBOOK.md](RUNBOOK.md) for detailed import instructions.

---

## Service Configuration

### Step 1: Verify SlabCrop Integration

1. **Check SlabCrop Installation**
   - Open SlabCrop application
   - Verify output folder setting matches `.env` configuration
   - Note: SlabCrop output folder is typically `D:\SlabCrop\output`

2. **Create Test Image**
   - Process a test slab image through SlabCrop
   - Verify image appears in output folder
   - Check image format (should be .png, .jpg, or .jpeg)

3. **Verify Watch Folder Path**
   ```bash
   # Check if folder exists
   dir D:\SlabCrop\output
   ```

### Step 2: Configure Windows Firewall

SlabHub needs to accept incoming connections on port 8000.

**Option 1: Allow Python through Firewall (Recommended)**

1. Open Windows Defender Firewall
2. Click "Allow an app or feature through Windows Defender Firewall"
3. Click "Change settings"
4. Click "Allow another app..."
5. Browse to: `C:\SlabHub\venv\Scripts\python.exe`
6. Add the app
7. Ensure both "Private" and "Public" are checked
8. Click OK

**Option 2: Create Specific Firewall Rule**

Run PowerShell as Administrator:
```powershell
New-NetFirewallRule -DisplayName "SlabHub Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**Option 3: Disable Firewall for Private Networks (Testing Only)**
- Not recommended for production
- Only use for initial testing

### Step 3: Test Printer Connection (Optional)

1. **Install PM-241BT Driver**
   - Install manufacturer-provided driver
   - Connect printer via USB or Bluetooth
   - Set as default printer (optional)

2. **Print Test Page**
   ```bash
   # From Windows
   # Go to Printers & Scanners
   # Select PM-241BT
   # Print test page
   ```

3. **Configure Label Size**
   - In printer properties, set paper size to 4x6 inches
   - Verify DPI is set to 203

---

## Network Configuration

### Step 1: Find Computer IP Address

```bash
# Run in Command Prompt
ipconfig
```

Look for "IPv4 Address" under your active network adapter (usually Ethernet or Wi-Fi). Example: `192.168.1.100`

### Step 2: Update PUBLIC_BASE_URL

Edit `.env` file and update:
```env
PUBLIC_BASE_URL=http://192.168.1.100:8000
```

Replace `192.168.1.100` with your actual IP address.

### Step 3: Test Network Connectivity

From another device on the same network:

```bash
# Test if computer is reachable
ping 192.168.1.100

# Should see replies if network is configured correctly
```

### Step 4: Configure Static IP (Recommended for Production)

To prevent IP address changes:

1. Open Network Connections
2. Right-click your network adapter → Properties
3. Select "Internet Protocol Version 4 (TCP/IPv4)" → Properties
4. Select "Use the following IP address"
5. Enter:
   - IP address: 192.168.1.100 (or your current IP)
   - Subnet mask: 255.255.255.0 (typically)
   - Default gateway: Your router's IP (usually 192.168.1.1)
   - Preferred DNS: 8.8.8.8
   - Alternate DNS: 8.8.4.4

### Step 5: Configure Router (Optional)

For external access or port forwarding:
- Log into router admin panel
- Set up port forwarding: External port 80 → Internal 192.168.1.100:8000
- Not required for LAN-only deployment

---

## Starting Services

### Method 1: Using Start Script (Recommended)

```bash
# From C:\SlabHub with virtual environment active
python scripts/start_services.py
```

This script:
- Starts FastAPI server on configured port
- Enables watch folder service (if configured)
- Provides graceful shutdown handling
- Logs all activity

### Method 2: Direct Uvicorn Launch

```bash
# From C:\SlabHub
python backend/app/main.py
```

Or:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Method 3: Background Service (Production)

For running as a Windows service, use NSSM (Non-Sucking Service Manager):

1. Download NSSM: https://nssm.cc/download
2. Extract to `C:\SlabHub\nssm`
3. Run as administrator:
   ```bash
   nssm install SlabHub
   ```
4. Configure:
   - Path: `C:\SlabHub\venv\Scripts\python.exe`
   - Startup directory: `C:\SlabHub`
   - Arguments: `scripts\start_services.py`
   - Service name: SlabHub
5. Set to start automatically

### Verify Services Are Running

```bash
# Check health endpoint
curl http://localhost:8000/health

# Or open in browser:
# http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "watch_folder_enabled": true,
  "watch_folder_running": true,
  "public_base_url": "http://192.168.1.100:8000"
}
```

---

## Testing Checklist

### Pre-Launch Testing

Run the comprehensive system test:
```bash
python scripts/test_system.py
```

### Manual Testing Checklist

#### Database Tests
- [ ] Database file exists (`data/slabhub.db`)
- [ ] Can query slabs table
- [ ] Import log tracking works

#### Image Processing Tests
- [ ] Place test image in SlabCrop output folder
- [ ] Verify watch folder detects it (check logs)
- [ ] Verify slab is created in database
- [ ] Verify image is archived to `data/archive`
- [ ] Check perceptual hash is calculated

#### QR Code Tests
- [ ] QR codes are generated for new slabs
- [ ] QR code files exist in `data/qr/`
- [ ] Scan QR code with phone camera
- [ ] Verify redirects to correct slab page
- [ ] Test from phone on same network

#### Label Tests
- [ ] Generate label via admin interface
- [ ] Verify PDF is created in `data/labels/`
- [ ] Open PDF and verify layout
- [ ] Print to PM-241BT printer (if available)
- [ ] Verify label is readable and properly formatted

#### API Tests
- [ ] GET /health returns healthy status
- [ ] GET /api/v1/slabs returns slab list
- [ ] GET /api/v1/slabs/{public_id} returns slab details
- [ ] POST /api/v1/slabs creates new slab
- [ ] API documentation accessible at /docs

#### Interface Tests
- [ ] Admin interface loads: http://192.168.1.100:8000/admin
- [ ] Kiosk interface loads: http://192.168.1.100:8000/kiosk
- [ ] Can browse slabs in kiosk
- [ ] Can view slab details
- [ ] Can search/filter slabs

#### Network Access Tests
- [ ] Access from another computer on LAN
- [ ] Access from mobile device on same Wi-Fi
- [ ] QR codes work from mobile devices
- [ ] Page loads are reasonably fast (<2 seconds)

#### Watch Folder Tests
- [ ] Copy image to SlabCrop output folder
- [ ] Wait 5 seconds
- [ ] Check logs for processing message
- [ ] Verify slab appears in admin interface
- [ ] Verify image moved to archive

---

## Launch Day Procedures

### Morning Checklist (Before Business Hours)

**T-2 hours before opening:**

1. **System Startup**
   ```bash
   cd C:\SlabHub
   venv\Scripts\activate
   python scripts/start_services.py
   ```

2. **Verify Health**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check Logs**
   ```bash
   # Check for any startup errors
   type data\logs\slabhub.log
   ```

4. **Test Core Functions**
   - Visit admin interface
   - Visit kiosk interface
   - Test QR code scan
   - Generate one test label
   - Process one test image

5. **Network Verification**
   - Test access from mobile device
   - Test access from another computer
   - Verify QR codes work

6. **Printer Check**
   - Print one test label
   - Verify printer has enough thermal paper
   - Check printer connectivity

**T-30 minutes:**

7. **Final System Check**
   ```bash
   python scripts/test_system.py
   ```

8. **Monitor Logs**
   ```bash
   # Keep log window open for monitoring
   Get-Content data\logs\slabhub.log -Wait
   ```

9. **Prepare Support**
   - Have DEPLOYMENT.md open
   - Have RUNBOOK.md open
   - Have restart script ready
   - Have backup plan ready

### During Business Hours

1. **Monitor Logs**
   - Keep an eye on log output
   - Watch for errors or warnings
   - Note any performance issues

2. **Watch for Issues**
   - Slow page loads
   - QR code scan failures
   - Image processing failures
   - Database errors

3. **Quick Response Procedures**
   - For minor issues: Check logs, restart service
   - For major issues: Execute rollback plan
   - Document all issues for post-launch review

### End of Day

1. **Review Logs**
   ```bash
   type data\logs\slabhub.log | findstr "ERROR"
   type data\logs\slabhub.log | findstr "WARNING"
   ```

2. **Backup Database**
   ```bash
   copy data\slabhub.db data\backups\slabhub_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db
   ```

3. **Statistics Review**
   - How many slabs processed?
   - How many QR code scans?
   - Any errors or failures?
   - System performance metrics?

---

## Troubleshooting

### Service Won't Start

**Symptom:** `python scripts/start_services.py` fails

**Solutions:**
1. Check if port 8000 is already in use:
   ```bash
   netstat -ano | findstr :8000
   ```
2. Kill conflicting process:
   ```bash
   taskkill /PID <process_id> /F
   ```
3. Check virtual environment is activated:
   ```bash
   # Should show (venv) in prompt
   ```
4. Verify all dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```
5. Check `.env` file exists and is valid
6. Review logs for specific error:
   ```bash
   type data\logs\slabhub.log
   ```

### Watch Folder Not Working

**Symptom:** Images placed in SlabCrop folder aren't imported

**Solutions:**
1. Verify watch folder is enabled in `.env`:
   ```env
   ENABLE_WATCH_FOLDER=true
   ```
2. Check SlabCrop output path is correct:
   ```bash
   dir D:\SlabCrop\output
   ```
3. Verify folder permissions (read/write access)
4. Check logs for watch folder errors:
   ```bash
   type data\logs\slabhub.log | findstr "watch"
   ```
5. Restart service to reinitialize watch folder
6. Manually trigger import as test:
   ```bash
   python scripts/import_metadata.py --file test.json
   ```

### QR Codes Don't Work

**Symptom:** Scanning QR code doesn't load page or shows error

**Solutions:**
1. Verify `PUBLIC_BASE_URL` in `.env` matches your IP:
   ```env
   PUBLIC_BASE_URL=http://192.168.1.100:8000
   ```
2. Test URL manually in phone browser:
   - Open `http://192.168.1.100:8000/health`
   - Should show health status
3. Ensure phone is on same Wi-Fi network
4. Check Windows Firewall isn't blocking connections
5. Verify service is running:
   ```bash
   curl http://localhost:8000/health
   ```
6. Regenerate QR code for test slab:
   ```bash
   # Via admin interface or API
   ```

### Database Errors

**Symptom:** Database connection errors or "locked database"

**Solutions:**
1. Check database file exists:
   ```bash
   dir data\slabhub.db
   ```
2. Verify no other processes have database locked:
   - Close any database browsers
   - Restart SlabHub service
3. Check disk space:
   ```bash
   dir C:\
   ```
4. Restore from backup if corrupted:
   ```bash
   copy data\backups\slabhub_latest.db data\slabhub.db
   ```
5. Reinitialize if no backup:
   ```bash
   python scripts/init_db.py
   ```

### Network Access Issues

**Symptom:** Can't access from other devices

**Solutions:**
1. Verify firewall rule:
   ```powershell
   Get-NetFirewallRule | Where-Object {$_.DisplayName -eq "SlabHub Server"}
   ```
2. Test from server itself:
   ```bash
   curl http://localhost:8000/health
   ```
3. Test from server using IP:
   ```bash
   curl http://192.168.1.100:8000/health
   ```
4. Verify IP address hasn't changed:
   ```bash
   ipconfig
   ```
5. Check router settings (no AP isolation)
6. Temporarily disable firewall to test:
   ```bash
   # Turn off, test, then turn back on
   ```

### Printer Issues

**Symptom:** Labels won't print or print incorrectly

**Solutions:**
1. Verify printer is online:
   - Check Printers & Scanners in Windows
   - Print test page
2. Check label size configuration:
   ```env
   LABEL_SIZE=4x6
   LABEL_DPI=203
   ```
3. Verify PDF is generated:
   ```bash
   dir data\labels
   ```
4. Open PDF manually and print
5. Check printer driver is up to date
6. Verify thermal paper is loaded correctly
7. Check USB/Bluetooth connection

### Performance Issues

**Symptom:** Slow page loads or timeouts

**Solutions:**
1. Check system resources:
   - Open Task Manager
   - Check CPU, RAM, Disk usage
2. Review log for performance warnings:
   ```bash
   type data\logs\slabhub.log | findstr "slow"
   ```
3. Optimize database:
   ```sql
   VACUUM;
   ANALYZE;
   ```
4. Clear old logs and archives:
   ```bash
   del data\logs\*.log.old
   ```
5. Check disk space:
   ```bash
   dir C:\
   ```
6. Restart service

---

## Backup Procedures

### Daily Backup

**Automated Script:** Create `scripts/backup.bat`:
```batch
@echo off
set BACKUP_DIR=C:\SlabHub\data\backups
set DATE=%date:~-4,4%%date:~-10,2%%date:~-7,2%

REM Create backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Backup database
copy C:\SlabHub\data\slabhub.db "%BACKUP_DIR%\slabhub_%DATE%.db"

REM Backup .env file
copy C:\SlabHub\.env "%BACKUP_DIR%\.env_%DATE%.backup"

REM Keep only last 7 days
forfiles /p "%BACKUP_DIR%" /m slabhub_*.db /d -7 /c "cmd /c del @path"

echo Backup completed: %DATE%
```

Run manually or schedule with Task Scheduler:
```bash
scripts\backup.bat
```

### Manual Backup

```bash
# Backup database
copy data\slabhub.db data\backups\slabhub_manual.db

# Backup entire data directory
xcopy data data_backup\ /E /I

# Backup configuration
copy .env .env.backup
```

### Backup Critical Files
- `data/slabhub.db` - Database
- `.env` - Configuration
- `data/logs/` - Logs (optional, for audit)
- `data/labels/` - Generated labels (optional)
- `data/qr/` - QR codes (can be regenerated)

### Offsite Backup

For production, copy backups to:
- External hard drive
- Network share
- Cloud storage (Dropbox, OneDrive, etc.)

```bash
# Copy to network share
xcopy data\backups\ \\NetworkShare\SlabHubBackups\ /E /I /Y

# Copy to external drive
xcopy data\backups\ E:\SlabHubBackups\ /E /I /Y
```

---

## Rollback Plan

### When to Rollback
- Critical system failures
- Data corruption
- Unrecoverable errors
- Deployment issues that can't be fixed quickly

### Rollback Procedure

**Step 1: Stop Current Services**
```bash
# Press Ctrl+C if running in terminal
# Or kill process:
taskkill /IM python.exe /F
```

**Step 2: Restore Database**
```bash
cd C:\SlabHub

# Find latest backup
dir data\backups\slabhub_*.db

# Restore backup (replace YYYYMMDD with actual date)
copy data\backups\slabhub_YYYYMMDD.db data\slabhub.db /Y
```

**Step 3: Restore Configuration**
```bash
# If .env was changed
copy .env.backup .env
```

**Step 4: Restart Services**
```bash
venv\Scripts\activate
python scripts/start_services.py
```

**Step 5: Verify**
```bash
curl http://localhost:8000/health
```

**Step 6: Test Core Functions**
- Access admin interface
- Access kiosk
- Test QR code
- Check logs

### Emergency Contacts

Have these ready for launch day:
- System administrator
- Network administrator
- Python developer (if available)
- Hardware support (for printer issues)

### Communication Plan

If rollback is necessary:
1. Notify all users immediately
2. Provide estimated downtime
3. Update stakeholders on progress
4. Document issues for post-mortem
5. Communicate when system is back online

---

## Post-Deployment

### Week 1 Monitoring

**Daily Tasks:**
- Review logs for errors
- Check system health endpoint
- Verify backups are running
- Monitor disk space
- Check performance metrics

**Weekly Tasks:**
- Review import logs
- Analyze QR code usage
- Check label generation statistics
- Performance optimization
- Update documentation based on issues found

### Optimization

After first week:
1. Analyze most common issues
2. Optimize database queries if needed
3. Adjust watch folder timing if needed
4. Review and update firewall rules
5. Consider performance tuning

### Documentation Updates

Keep these documents updated:
- Add new troubleshooting scenarios
- Document configuration changes
- Update network topology
- Record all customizations
- Maintain issue log

---

## Support and Maintenance

### Regular Maintenance

**Daily:**
- Check logs for errors
- Verify service is running
- Monitor disk space

**Weekly:**
- Run backup manually
- Review system health
- Clean old logs
- Update documentation

**Monthly:**
- Review and archive old data
- Update dependencies (if needed)
- Performance review
- Security review

### Getting Help

1. Check this documentation
2. Review logs: `data\logs\slabhub.log`
3. Check RUNBOOK.md for common tasks
4. Review FastAPI docs: https://fastapi.tiangolo.com/
5. Contact system administrator

---

## Conclusion

This deployment guide provides comprehensive instructions for launching SlabHub on Monday. Follow each section carefully, complete all checklists, and have the troubleshooting section handy during launch day.

**Key Success Factors:**
- Thorough pre-deployment testing
- Proper network configuration
- Reliable backup procedures
- Quick troubleshooting response
- Clear communication plan

Good luck with your Monday launch!
