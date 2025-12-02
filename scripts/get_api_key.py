#!/usr/bin/env python3
"""Get first client API key from database."""
import sys
import os

sys.path.insert(0, '/app/libs/vizu_db_connector/src')
sys.path.insert(0, '/app/libs/vizu_models/src')

from sqlmodel import Session, create_engine, select
from vizu_models import ClienteVizu

engine = create_engine(os.environ['DATABASE_URL'])
with Session(engine) as s:
    c = s.exec(select(ClienteVizu).limit(1)).first()
    if c:
        print(c.api_key)
    else:
        sys.exit(1)
