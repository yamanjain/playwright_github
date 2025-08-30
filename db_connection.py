import psycopg2
import os

def make_db_connection():
    db_connection_url = os.getenv("DB_CONNECTION_URL")
    # Connect to Aiven PostgreSQL
    conn = psycopg2.connect(db_connection_url)
    cur = conn.cursor()
    return conn, cur

    # db_config = {
    #     "host": os.getenv("DB_HOST"),
    #     "port": int(os.getenv("DB_PORT", 3306)),
    #     "user": os.getenv("DB_USER"),
    #     "passwd": os.getenv("DB_PASSWORD"),
    #     "db": os.getenv("DB_NAME")
    # }
    #
    # ssl_config = {"ca": os.getenv("DB_SSL_CA")} if os.getenv("DB_SSL_CA") else None
    #
    # # Connect to MySQL
    # conn = MySQLdb.connect(**db_config, ssl=ssl_config)
    # cur = conn.cursor()
    # return conn, cur
