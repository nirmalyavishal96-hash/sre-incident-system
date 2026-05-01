from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL
import redis
from app.config import REDIS_URL

import time
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://user:password@postgres:5432/ims_db"

for i in range(10):
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        conn.close()
        print("DB Connected")
        break
    except Exception as e:
        print("Waiting for DB...")
        time.sleep(3)
else:
    raise Exception("Could not connect to DB")



SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)