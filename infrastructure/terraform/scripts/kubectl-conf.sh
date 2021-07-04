#!/usr/bin/env bash

set -ex

WORKSPACE=$1
PUBLIC_IP=$2
PRIVATE_IP=$3
KEY_FILE=$4

scp -i ${KEY_FILE} -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${PUBLIC_IP}:/etc/kubernetes/admin.conf .
sed -e "s/${PRIVATE_IP}/${PUBLIC_IP}/g" admin.conf > ${WORKSPACE}.conf
rm admin.conf