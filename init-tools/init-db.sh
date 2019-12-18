#!/bin/bash

# Script to create a new database user for the PIPELINE scripts.
#
# Usage: init-db.sh HOST PORT ADMINUSER ADMINPSW USER USERPSW DBNAME
# Eg:    init-db.sh localhost postgres askap askappsw askapdb
#
# This will create a postgresql user "askap" with login password "askappsw"
# a database "askapdb" and grant to "askap" user all the priveleges to "askapdb"

if [ $# -ne 7 ]
then
	echo "Usage: init-db.sh HOST PORT ADMINUSER ADMINPSW USER USERPSW DBNAME"
	echo "Eg:    init-db.sh localhost 5432 postgres postgres askap askappsw askapdb"
    echo ""
    echo "Help: This will create a postgresql user 'askap' with login password 'askappsw'"
    echo "      and a database 'askapdb' and grant to 'askap' user all the priveleges to 'askapdb'"
    echo "Note: the arguments need to be passed in that order because"
    echo "\$1  ->  HOST in which the database runs"
    echo "\$2  ->  PORT to connect to on the host"
    echo "\$3  ->  ADMINUSER the administrator user of the database"
    echo "\$4  ->  ADMINPSW the administrator password"
    echo "\$5  ->  USER the user to create"
    echo "\$6  ->  USERPSW the user password"
    echo "\$6  ->  DBNAME the database name to create inside the database"
	[ $PS1 ] && return || exit
fi

echo "connecting to PostgreSQL on '$1:$2' as admin '$3'"
echo "creating user '$5' with login password '$6' and give it createdb privileges"
PGPASSWORD=$4 psql -h $1 -p $2 -U $3 -c "CREATE ROLE $5 WITH LOGIN PASSWORD '$6' CREATEDB"

echo "************************************"
echo "creating db '$7', enable Q3C plugin"
PGPASSWORD=$6 createdb -h $1 -p $2 -U $5 $7
PGPASSWORD=$4 psql -h $1 -p $2 -U $3 -d $7 -c 'CREATE EXTENSION q3c'
