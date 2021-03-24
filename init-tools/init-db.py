import argparse
import psycopg2
from psycopg2 import sql


parser = argparse.ArgumentParser(
    description=(
        "Initialize a PostgreSQL database for VAST Pipeline use. Creates a new"
        " superuser and creates a new database owned by the new superuser."
    )
)
parser.add_argument("host", help="database host")
parser.add_argument("port", type=int, help="database port")
parser.add_argument(
    "admin_username", metavar="admin-username", help="database administrator username"
)
parser.add_argument(
    "admin_password", metavar="admin-password", help="database administrator password"
)
parser.add_argument(
    "username", help="username for the new user/role to create for the VAST Pipeline"
)
parser.add_argument(
    "password", help="password for the new user/role to create for the VAST Pipeline"
)
parser.add_argument(
    "database_name",
    metavar="database-name",
    help="name of the new database to create for the VAST Pipeline",
)
args = parser.parse_args()

conn = psycopg2.connect(
    host=args.host,
    port=args.port,
    user=args.admin_username,
    password=args.admin_password,
    dbname=args.admin_username,
)
conn.autocommit = True

with conn.cursor() as cur:
    print("Creating new user/role {} ...".format(args.username))
    try:
        cur.execute(
            sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD %s SUPERUSER").format(
                sql.Identifier(args.username)
            ),
            (args.password,),
        )
    except psycopg2.errors.DuplicateObject:
        print("User/role {} already exists".format(args.username))
    print("Creating new database {} ...".format(args.database_name))
    try:
        cur.execute(
            sql.SQL("CREATE DATABASE {} WITH OWNER = {}").format(
                sql.Identifier(args.database_name),
                sql.Identifier(args.username),
            )
        )
    except psycopg2.errors.DuplicateDatabase:
        print("Database {} already exists".format(args.database_name))
print("Done!")
