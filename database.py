# import os
# from sqlalchemy import create_engine
# DB_URL = os.environ.get('DATABASE_URL', "mysql+mysqlconnector://sql7822943:sIl2Tba59y@sql7.freesqldatabase.com:3306/sql7822943")
# engine = create_engine(DB_URL)


from sqlalchemy import create_engine
DB_URL = "mysql+mysqlconnector://root@localhost/nomadcash"
engine = create_engine(DB_URL)