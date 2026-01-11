#!/usr/bin/env python3
"""Reset rate limit by fingerprint"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '/Users/teebox-admin/Code/jankyard')
from app.core.config import config

def reset_rate_limit_by_fingerprint(fingerprint: str):
    """Reset rate limit for a fingerprint"""
    engine = create_engine(config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Delete all rate limit entries for this fingerprint
        result = session.execute(
            text("DELETE FROM rate_limits WHERE identifier = :fingerprint"),
            {"fingerprint": fingerprint}
        )
        session.commit()
        
        print(f"✅ Reset rate limit for fingerprint")
        print(f"   Deleted {result.rowcount} rate limit entries")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Your browser fingerprint
    reset_rate_limit_by_fingerprint("d0e8c59e923b4174f9ea88426f66cc4e16bc83992f466c7d6d96e17a899bcadc")
