#!/usr/bin/env python3
"""Check rate limit entries"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '/Users/teebox-admin/Code/jankyard')
from app.core.config import config

def check_rate_limits():
    """Check all rate limit entries"""
    engine = create_engine(config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all recent rate limit entries
        result = session.execute(
            text("""
                SELECT identifier, identifier_type, endpoint, window_type, 
                       request_count, window_start 
                FROM rate_limits 
                ORDER BY updated_at DESC 
                LIMIT 20
            """)
        )
        
        print("\n📊 Recent Rate Limit Entries:")
        print("-" * 80)
        for row in result:
            print(f"Identifier: {row[0]}")
            print(f"  Type: {row[1]}, Endpoint: {row[2]}")
            print(f"  Window: {row[3]}, Count: {row[4]}, Start: {row[5]}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_rate_limits()
