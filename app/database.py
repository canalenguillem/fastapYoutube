from sqlalchemy import create_engine, MetaData
from databases import Database

DATABASE_URL = "sqlite:///test.db"

engine = create_engine(DATABASE_URL)
metadata = MetaData()

database = Database(DATABASE_URL)
