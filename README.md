> **IMPORTANT — REQUIRED READING**
>
> Before making any changes to this repository, you MUST read:
> - PRE_PHASE0_BASELINE.md
> - AGENTS_RULES_OF_ENGAGEMENT.md
> - PHASE_EXECUTION_PLAN.md

# SlabHub - Stone Slab Inventory Management System

SlabHub is a comprehensive inventory management system designed specifically for stone slab businesses. It integrates seamlessly with SlabCrop for automated image processing, features QR code generation for easy slab identification, and provides both admin and public-facing kiosk interfaces.

## Features

### Core Functionality
- **Automated Import**: Integrates with SlabCrop to automatically process and catalog new slab images
- **Watch Folder Service**: Monitors SlabCrop output directory for new images and imports them automatically
- **Duplicate Detection**: Uses perceptual image hashing to prevent duplicate entries
- **QR Code System**: Generates unique QR codes for each slab, enabling easy mobile lookup
- **Label Printing**: Creates professional 4x6" thermal labels for PM-241BT printer
- **Public Kiosk**: Customer-facing interface for browsing available slabs
- **Admin Dashboard**: Comprehensive management interface for inventory control

### Image Processing
- Automatic image validation (dimensions, format, corruption detection)
- Perceptual hash calculation for duplicate detection
- Support for multiple image formats (PNG, JPG, JPEG, TIFF, BMP)
- Configurable quality thresholds

### Data Management
- Full slab metadata tracking (stone type, finish, dimensions, location, etc.)
- Import logging and audit trails
- Batch import from JSON metadata files
- Flexible field mapping for various data sources

### Integration
- **SlabCrop Integration**: Seamless connection with SlabCrop image processing software
- **LAN Access**: Configure for network access from multiple devices
- **Mobile Scanning**: QR codes work with any smartphone camera app

## Technology Stack

### Backend
- **FastAPI**: Modern, high-performance Python web framework
- **SQLAlchemy**: SQL toolkit and ORM for database operations
- **SQLite**: Lightweight, serverless database (production-ready for single-site deployments)
- **Pydantic**: Data validation using Python type annotations

### Image Processing
- **Pillow (PIL)**: Image manipulation and validation
- **ImageHash**: Perceptual hashing for duplicate detection
- **QRCode**: QR code generation
- **ReportLab**: PDF label generation

### File System
- **Watchdog**: File system monitoring for automatic imports

### Frontend
- **Jinja2 Templates**: Server-side rendered HTML
- **FastAPI Static Files**: Asset serving

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Windows 10/11 (for SlabCrop integration)
- PM-241BT thermal printer (for label printing, optional)
- SlabCrop software installed (optional but recommended)

### Installation

1. **Clone or Extract the Repository**
   ```bash
   cd D:\SlabHub
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   Create a `.env` file in the project root:
   ```env
   # Application
   PUBLIC_BASE_URL=http://192.168.1.100:8000
   DEBUG=false
   HOST=0.0.0.0
   PORT=8000

   # Database
   DATABASE_URL=sqlite:///./data/slabhub.db

   # SlabCrop Integration
   SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output
   ENABLE_WATCH_FOLDER=false

   # Paths
   LABEL_OUTPUT_FOLDER=./data/labels
   QR_OUTPUT_FOLDER=./data/qr
   PROCESSED_ARCHIVE_FOLDER=./data/archive

   # Logging
   LOG_LEVEL=INFO
   LOG_FILE=./data/logs/slabhub.log
   ```

5. **Initialize Database**
   ```bash
   python scripts/init_db.py
   ```

6. **Start the Application**
   ```bash
   python scripts/start_services.py
   ```

   The application will be available at:
   - Admin Interface: `http://localhost:8000/admin`
   - Kiosk Interface: `http://localhost:8000/kiosk`
   - API Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

## Running the Application

### Development Mode
For development with auto-reload:
```bash
python backend/app/main.py
```

### Production Mode
Using the startup script (recommended):
```bash
python scripts/start_services.py
```

Or using uvicorn directly:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Enable Watch Folder Service
The watch folder service automatically monitors SlabCrop output and imports new images. It's controlled by the `.env` file:
```env
ENABLE_WATCH_FOLDER=true
SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output
```

## Developer Setup

### Environment Requirements
- **SLABHUB_ROOT**: Must be set to `D:\SlabHub` (enforced at startup)
- All data is stored under `D:\SlabHub\data\`
- Never run from `C:\` or any other drive

### Validate Installation
Run the import smoke test to verify all packages are correctly configured:
```bash
python scripts/import_smoke_test.py
```

Expected output:
```
==================================================
SlabHub Import Smoke Test
==================================================

[OK] backend.app.schemas
[OK] backend.app.models
[OK] backend.app.routers
[OK] backend.app.services
[OK] backend.app.utils
[OK] backend.app.core
[OK] backend.app.config
[OK] backend.app.version (v2.02)

==================================================
PASSED: All imports successful
```

### Verify Health Endpoints
After starting the server, verify health endpoints:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/storage
```

All endpoints should return HTTP 200 with JSON status information.

## API Documentation

### Interactive API Docs
FastAPI provides automatic interactive documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Slabs API (`/api/v1/slabs`)
- `GET /api/v1/slabs` - List all slabs (with pagination and filtering)
- `GET /api/v1/slabs/{public_id}` - Get single slab details
- `POST /api/v1/slabs` - Create new slab
- `PUT /api/v1/slabs/{public_id}` - Update slab
- `DELETE /api/v1/slabs/{public_id}` - Delete slab
- `POST /api/v1/slabs/{public_id}/label` - Generate label for slab

#### Admin Routes (`/admin`)
- `GET /admin` - Admin dashboard
- `GET /admin/slabs` - Slab management
- `GET /admin/imports` - Import history

#### Kiosk Routes (`/kiosk`)
- `GET /kiosk` - Public slab browser
- `GET /kiosk/slab/{public_id}` - Slab detail page (QR code destination)

#### Short URLs (`/s`)
- `GET /s/{public_id}` - Short URL redirect for QR codes

#### Health Check
- `GET /health` - System health and status

## Project Structure

```
SlabHub/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI application entry point
│       ├── config.py            # Configuration management
│       ├── schemas.py           # Pydantic schemas
│       ├── crud.py              # Database operations
│       ├── models/              # SQLAlchemy models
│       │   ├── base.py          # Base model class
│       │   ├── slab.py          # Slab model
│       │   ├── inventory.py     # Inventory model
│       │   └── import_log.py    # Import tracking model
│       ├── routers/             # API routes
│       │   ├── slabs.py         # Slab API endpoints
│       │   ├── admin.py         # Admin interface
│       │   └── kiosk.py         # Public kiosk
│       ├── services/            # Business logic
│       │   ├── watch_folder.py  # File system monitoring
│       │   └── import_processor.py  # Image import processing
│       ├── utils/               # Utility functions
│       │   ├── image_hash.py    # Perceptual hashing
│       │   ├── image_validator.py  # Image validation
│       │   ├── qr_generator.py  # QR code generation
│       │   └── label_printer.py # PDF label generation
│       ├── static/              # Static assets (CSS, JS, images)
│       └── templates/           # Jinja2 HTML templates
├── scripts/                     # Utility scripts
│   ├── init_db.py              # Database initialization
│   ├── import_metadata.py      # JSON metadata import
│   ├── verify_import.py        # Import verification
│   ├── start_services.py       # Service startup script
│   └── test_system.py          # System testing
├── data/                        # Data directory (created at runtime)
│   ├── slabhub.db              # SQLite database
│   ├── labels/                 # Generated labels
│   ├── qr/                     # Generated QR codes
│   ├── archive/                # Processed images
│   └── logs/                   # Application logs
├── .env                        # Environment configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── DEPLOYMENT.md              # Deployment guide
└── RUNBOOK.md                 # Operations manual
```

## Configuration

All configuration is managed through environment variables in the `.env` file. See the `.env.example` or the Quick Start section for a complete example.

### Key Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `PUBLIC_BASE_URL` | Public URL for QR codes | `http://localhost:8000` |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/slabhub.db` |
| `SLABCROP_OUTPUT_FOLDER` | SlabCrop output directory | `D:/SlabCrop/output` |
| `ENABLE_WATCH_FOLDER` | Enable automatic monitoring | `true` |
| `LABEL_SIZE` | Label dimensions | `4x6` |
| `LABEL_DPI` | Label resolution | `203` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Common Tasks

### Import Existing Slab Library
```bash
python scripts/import_metadata.py --file path/to/stone-identifications.json
```

### Preview Import (Dry Run)
```bash
python scripts/import_metadata.py --file data.json --dry-run
```

### Verify Import
```bash
python scripts/verify_import.py
```

### Generate Label for Slab
Use the admin interface or API:
```bash
curl -X POST http://localhost:8000/api/v1/slabs/{public_id}/label
```

### View Logs
```bash
# Real-time monitoring
tail -f data/logs/slabhub.log

# On Windows
Get-Content data/logs/slabhub.log -Wait
```

### Test System
```bash
python scripts/test_system.py
```

## Network Access (LAN)

To access SlabHub from other devices on your network:

1. Find your computer's IP address:
   ```bash
   ipconfig
   # Look for IPv4 Address, e.g., 192.168.1.100
   ```

2. Update `.env`:
   ```env
   HOST=0.0.0.0
   PUBLIC_BASE_URL=http://192.168.1.100:8000
   ```

3. Configure Windows Firewall:
   - Allow inbound connections on port 8000
   - Or disable firewall for private networks (testing only)

4. Access from other devices:
   - `http://192.168.1.100:8000/kiosk`

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install dev dependencies
4. Make changes
5. Run tests: `python scripts/test_system.py`
6. Submit pull request

## Agent Onboarding

Before contributing code to SlabHub, you **must** read the [AGENTS_ONBOARDING.md](AGENTS_ONBOARDING.md) document.  It contains mandatory rules of engagement, definition of done, version bump enforcement, and governance policies for agents working on this project.  You must create a restore point before making any changes and follow the stability and maturity checklist in strict numerical order.

### Code Style
- Follow PEP 8 guidelines
- Use type hints where applicable
- Add docstrings to functions and classes
- Keep functions focused and single-purpose

### Database Migrations
When modifying models:
1. Update model in `backend/app/models/`
2. Create Alembic migration (if using Alembic)
3. Test migration locally
4. Document changes in commit message

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Find process using port 8000
netstat -ano | findstr :8000
# Kill the process
taskkill /PID <process_id> /F
```

**Watch folder not working**
- Verify `SLABCROP_OUTPUT_FOLDER` path is correct
- Check folder permissions
- Review logs for errors
- Ensure `ENABLE_WATCH_FOLDER=true`

**QR codes not working**
- Verify `PUBLIC_BASE_URL` matches your network setup
- Ensure phone and server are on same network
- Check firewall settings

**Label printing issues**
- Verify PM-241BT driver is installed
- Check printer connection (USB/Bluetooth)
- Verify `LABEL_SIZE=4x6` and `LABEL_DPI=203`
- Test with sample PDF first

For more detailed troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md) and [RUNBOOK.md](RUNBOOK.md).

## Support

For issues, questions, or contributions:
- Check the documentation in `DEPLOYMENT.md` and `RUNBOOK.md`
- Review application logs in `data/logs/slabhub.log`
- Check FastAPI documentation: https://fastapi.tiangolo.com/
- Review SQLAlchemy documentation: https://docs.sqlalchemy.org/

## License

[Add your license information here]

## Version

Current Version: 1.0.0 (Monday Launch - January 2026)
