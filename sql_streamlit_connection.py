import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
import logging
import toml

# For SQL errors detection
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# loading config.toml
config = toml.load('config.toml')

#The function will connect to the MySQL database (in GCP) and retrieves data from the gaia_data table
def get_data_from_sql():
    try:
        # Getting details of Db from config file
        db_config = config['database']
        username = db_config['username']
        password = db_config['password']
        host = db_config['host']
        dbname = db_config['dbname']

        # credentials for SQLAlchemy from the config file
        engine = create_engine(f'mysql+pymysql://{username}:{password}@{host}/{dbname}')
        
        # fetchhing all data from the gaia_data table
        query = "SELECT * FROM gaia_data"
        
        # Converting to pandas dataframe
        data = pd.read_sql(query, engine)
        return data
    except Exception as e:
        # Checking the errors for Streamlit
        st.error(f"Error connecting to MySQL: {e}")
        logger.error(f"Error connecting to MySQL: {e}")
        
        # If error - returning empty dataframe
        return pd.DataFrame()
