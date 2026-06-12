import configparser
from sqlalchemy import create_engine, inspect

cfg = configparser.ConfigParser()
cfg.read('alembic.ini')
url = cfg.get('alembic', 'sqlalchemy.url')

engine = create_engine(url)
inspector = inspect(engine)

tables = inspector.get_table_names()
print('blocks' in tables)
print('reports' in tables)
print('Tables found:', tables)
