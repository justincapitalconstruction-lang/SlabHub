#!/usr/bin/env python3
"""
Smoke test for SlabHub job system.

Quick validation that job creation, execution, and monitoring works.
Run this after deployment to verify job system integrity.

Usage:
    python tests/smoke_test_jobs.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_job_system():
    """Test basic job system functionality."""
    print("🔄 Testing SlabHub Job System...")

    try:
        # Import job system
        from backend.app.services.job_service import JobService, create_job, get_job
        from backend.app.models import SessionLocal
        print("✅ Job service imported successfully")

        # Create a test job
        db = SessionLocal()
        service = JobService(db)

        job = service.create_job(
            job_type="test_smoke",
            input_data={"test": "data"},
            priority=1,
            created_by="smoke_test"
        )
        print(f"✅ Created test job: {job.job_id}")

        # Retrieve the job
        retrieved = service.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_type == "test_smoke"
        print("✅ Job retrieval works")

        # Update progress
        service.update_progress(job, 50.0, "Halfway done")
        assert job.progress_percent == 50.0
        print("✅ Progress update works")

        # Complete the job
        service.complete_job(job, {"result": "success"})
        assert job.status == "completed"
        print("✅ Job completion works")

        # Check metrics
        metrics = service.get_job_metrics()
        assert "total_jobs" in metrics
        assert metrics["total_jobs"] >= 1
        print(f"✅ Job metrics: {metrics['total_jobs']} total jobs")

        # Cleanup
        db.delete(job)
        db.commit()
        print("✅ Cleanup completed")

        db.close()
        print("\n🎉 All job system tests passed!")
        return True

    except Exception as e:
        print(f"❌ Job system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_job_system()

    if success:
        print("\n🚀 Job system smoke test PASSED")
        sys.exit(0)
    else:
        print("\n💥 Job system smoke test FAILED")
        sys.exit(1)