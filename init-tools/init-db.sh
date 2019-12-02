#!/bin/bash

# Script to create a new database user for the PIPELINE scripts.
#
# Usage: createdb-user.sh HOST PORT ADMINUSER ADMINPSW USER USERPSW DBNAME
# Eg:    createdb-user.sh localhost postgres askap askappsw askapdb
#
# This will create a postgresql user "askap" with login password "askappsw"
# a database "askapdb" and grant to "askap" user all the priveleges to "askapdb"

if [ $# -ne 7 ]
then
	echo "Usage: createdb-user.sh HOST PORT ADMINUSER ADMINPSW USER USERPSW DBNAME"
	echo "Eg:    createdb-user.sh localhost 5432 postgres postgres askap askappsw askapdb"
    echo ""
    echo "Help: This will create a postgresql user 'askap' with login password 'askappsw'"
    echo "      and a database 'askapdb' and grant to 'askap' user all the priveleges to 'askapdb'"
	[ $PS1 ] && return || exit
fi

echo "connecting to PostgreSQL on '$1:$2' as admin '$3'"
echo "creating user '$5' with login password '$6' and give it createdb privileges"
PGPASSWORD=$4 psql -h $1 -p $2 -U $3 -c "CREATE ROLE $5 WITH LOGIN PASSWORD '$6' CREATEDB"

echo "************************************"
echo "creating db '$7', enable Q3C plugin"
PGPASSWORD=$6 createdb -h $1 -p $2 -U $5 $7
PGPASSWORD=$4 psql -h $1 -p $2 -U $3 -d $7 -c 'CREATE EXTENSION q3c'
