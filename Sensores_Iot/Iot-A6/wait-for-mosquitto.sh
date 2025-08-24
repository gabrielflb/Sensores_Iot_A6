#!/bin/sh
set -e

host="$1"
shift
cmd="$@"

echo " Aguardando Mosquitto em $host:1883..."
until nc -z "$host" 1883; do
  sleep 2
done

echo "Mosquitto disponível! Subindo backend..."
exec $cmd
