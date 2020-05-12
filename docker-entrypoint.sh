#!/bin/sh

set -e

execho() {
  echo "executing: $@"
  $@
}

exechon() {
  echo -n "executing: $@... "
  $@
  echo "OK"
}

execho pip install -e .
exechon wait-for "$DJANGO_DATABASE_HOST_POSTGRES:$DJANGO_DATABASE_PORT_POSTGRES" --timeout=60
exechon wait-for "$DJANGO_DATABASE_HOST_MYSQL:$DJANGO_DATABASE_PORT_MYSQL" --timeout=60

execho $@
