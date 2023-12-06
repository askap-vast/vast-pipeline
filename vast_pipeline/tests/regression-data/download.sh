#!/bin/bash

if [[ "$(ls)" =~ "EPOCH" ]]; then
  echo "ERROR: regression data appaears to already exist!"
  exit 1
fi

echo "WARNING: regression test data is ~600MB ..."
echo

TMPFILE=`mktemp`
TMPDIR=`mktemp -d`
curl 'https://unisyd-my.sharepoint.com/personal/tara_murphy_sydney_edu_au/_layouts/15/download.aspx?SourceUrl=%2Fpersonal%2Ftara%5Fmurphy%5Fsydney%5Fedu%5Fau%2FDocuments%2FVAST%20Storage%2Fpipeline%2Dtest%2Ddata%2Ezip' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Referer: https://unisyd-my.sharepoint.com/personal/tara_murphy_sydney_edu_au/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Ftara%5Fmurphy%5Fsydney%5Fedu%5Fau%2FDocuments%2FVAST%20Storage%2Fpipeline%2Dtest%2Ddata%2Ezip&parent=%2Fpersonal%2Ftara%5Fmurphy%5Fsydney%5Fedu%5Fau%2FDocuments%2FVAST%20Storage&ga=1' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: iframe' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Connection: keep-alive' -H 'Cookie: FedAuth=77u/PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48U1A+VjEzLDBoLmZ8bWVtYmVyc2hpcHx1cm4lM2FzcG8lM2Fhbm9uI2M5MjczOTc4OWNiNGM0M2RkYWM0OWQ0NGRhY2I5YWY3MDJkYTExMDRiODYzYzg2ZmVmODc0YTZhZmNmZWJjNGYsMCMuZnxtZW1iZXJzaGlwfHVybiUzYXNwbyUzYWFub24jYzkyNzM5Nzg5Y2I0YzQzZGRhYzQ5ZDQ0ZGFjYjlhZjcwMmRhMTEwNGI4NjNjODZmZWY4NzRhNmFmY2ZlYmM0ZiwxMzM0NjI5MjIzNDAwMDAwMDAsMCwxMzM0NjM3ODMzNDI3OTU5MjYsMC4wLjAuMCwyNTgsN2YxMjQ4Y2QtZjk5OS00M2ZiLWI5ZTUtNTZlMmZjZjFiNWQwLCwsM2RlN2Y0YTAtYTAzYy0yMDAwLWM3MDUtZWY0YjA3MTNkYThhLDNkZTdmNGEwLWEwM2MtMjAwMC1jNzA1LWVmNGIwNzEzZGE4YSwvc0YvWnFrU2MwR0V5QmROazd2OVl3LDAsMCwwLCwsLDI2NTA0Njc3NDM5OTk5OTk5OTksMCwsLCwsLCwwLCwxOTYyNjMsR0FkeFdYM3FnLXBsUDRlOVhCUDF5MTZpZmpVLFNtZVNSY1c0Q05LQlIzLy8vZndXUUVkdDN6cDN1VGVGT1hXYjhLTlFoYnhiZFVBaHRkNUFYRzRPTHdnS3RJYXc2WDh4Vnd1R28vSHNxYVQ2MkhSdDd4NFM1Vk5HeFY2dTM4eHNKL2w4c2pKa2U0M3lWSWtxRXlBZjZQVU54OW0xMkxYWHNuTC9IM1Y0dmF4OVFmSktsZjJ4Mi82eEdvNExIWEFxeXhyenppTkYyRlA3RG05RWJQQlE2Zi93d0dMYWtEaVNZUk9qWEJxbCsrcm0zaFdIVHdBR051WVd2RHdzbmE2QzZFbS81Y0dnaGZadnpTWEdKeVZjYnJzQ3pVL3pYMTRhT2MvbmpiNjRMeVdKZmFDbFRsdUZaT3kyWWIzV2FSNGtjeWZpOVhMdVk4dmVUckc0ZU5YMUVCeG9BOWpjZXNzcjYwQmRsakV6Z3JPQk5ad0pwQT09PC9TUD4=; MicrosoftApplicationsTelemetryDeviceId=7b442835-e333-4fa8-b9c3-219175ce28b2; ai_session=RMbbZZJRnPnpdAhkY963W+|1701818341013|1701818341013; MSFPC=GUID=29aabafd6ae84775aa40110631a2af5c&HASH=29aa&LV=202312&V=4&LU=1701818343559' -o ${TMPFILE}

echo "Unzipping archive to ${TMPDIR} ..."
unzip -q -d ${TMPDIR} ${TMPFILE}

echo "Moving data to relevant directory..."
mv ${TMPDIR}/VAST_PIPELINE_TEST_DATASET/* $(pwd)/.

echo "Deleting temporary files..."
rm -r ${TMPFILE} ${TMPDIR}

echo "Done."
