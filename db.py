import os
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()
db_pre = os.getenv('DATABASE_URL')
db = create_engine(db_pre)
#with db.connect() as f:
    #print(f)