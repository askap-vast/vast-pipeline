#!/bin/bash

if [[ "$(ls)" =~ "EPOCH" ]]; then
  echo "ERROR: regression data appaears to already exist!"
  exit 1
fi

echo "WARNING: regression test data is ~600MB ..."
echo

TMPFILE=`mktemp`
TMPDIR=`mktemp -d`
wget "http://www.physics.usyd.edu.au/~ddob1600/vast-pipeline/pipeline-test-data.zip" -O ${TMPFILE}

echo "Unzipping archive to ${TMPDIR} ..."
unzip -q -d ${TMPDIR} ${TMPFILE}

echo "Moving data to relevant directory..."
#mv ${TMPDIR}/VAST_PIPELINE_TEST_DATASET/* $(pwd)/.
mv ${TMPDIR}/pipeline-test-data/* $(pwd)/.

echo "Deleting temporary files..."
rm -r ${TMPFILE} ${TMPDIR}

echo "Done."
