from GraphEngine.db.connection import engine
from GraphEngine.db.models import Base

Base.metadata.create_all(bind=engine)

print("Database initialized")

#  python -m db.init_db (run it only once)