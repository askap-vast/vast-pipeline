#!/bin/bash

if [[ "$(ls)" =~ "EPOCH" ]]; then
  echo "ERROR: regression data appaears to already exist!"
  exit 1
fi

echo "WARNING: regression test data is ~600MB ..."
echo

TMPFILE=`mktemp`
TMPDIR=`mktemp -d`
wget "https://cloudstor.aarnet.edu.au/plus/s/xjh0aRr1EGY6Bt3/download" -O ${TMPFILE}

echo "Unzipping archive to ${TMPDIR} ..."
unzip -q -d ${TMPDIR} ${TMPFILE}

echo "Moving data to relevant directory..."
mv ${TMPDIR}/VAST_PIPELINE_TEST_DATASET/* $(pwd)/.

echo "Deleting temporary files..."
rm -r ${TMPFILE} ${TMPDIR}

echo "Done."
