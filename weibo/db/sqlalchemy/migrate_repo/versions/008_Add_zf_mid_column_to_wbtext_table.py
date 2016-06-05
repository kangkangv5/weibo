from sqlalchemy import *
from migrate import *


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = MetaData()
    meta.bind = migrate_engine

    # create column:

    wbtext = Table('wbtext', meta, autoload=True)
    zf_mid = Column('zf_mid', BigInteger)

    wbtext.create_column(zf_mid)



def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = MetaData()
    meta.bind = migrate_engine

    # create column:

    wbtext = Table('wbtext', meta, autoload=True)
    zf_mid = Column('zf_mid', BigInteger)

    wbtext.drop_column(zf_mid)
