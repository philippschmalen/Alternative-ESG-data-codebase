#!/bin/bash

# Exit if any of the intermediate steps fail
set -ex

# Extract "host" and "key_file" argument from the input into HOST shell variable
eval "$(jq -r '@sh "HOST=\(.host) KEY=\(.key)"')"

# Fetch the join command
CMD=$(ssh -v -i $KEY -oBatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    root@$HOST kubeadm token create --print-join-command)

# Safely produce a JSON object containing the join command.
# jq will ensure that the value is properly quoted
# and escaped to produce a valid JSON string.
jq -n --arg command "$CMD" '{"command":$command}'