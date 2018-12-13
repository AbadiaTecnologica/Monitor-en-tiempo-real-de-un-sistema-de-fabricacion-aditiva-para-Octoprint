import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tabledef import *

engine = create_engine('sqlite:///tutorial.db', echo=True)

# create a Session
Session = sessionmaker(bind=engine)
session = Session()

user = User("admin", "admin")
session.add(user)

user = User("operador", "operador")
session.add(user)

user = User("visor", "visor")
session.add(user)

# commit the record the database
session.commit()

session.commit()