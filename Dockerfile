FROM python:alpine3.11

ARG WORK_DIR=/run/django-reversion/

RUN apk update && apk upgrade && apk add \
build-base \
gcc \
mariadb-connector-c-dev \
postgresql-contrib \
postgresql-dev \
python-dev

RUN pip install -U pip \
django \
psycopg2 \
mysqlclient

RUN \
wget -q -O - https://raw.githubusercontent.com/eficode/wait-for/8d9b4446df0b71275ad1a1c68db0cc2bb6978228/wait-for > /bin/wait-for && \
sha256sum /bin/wait-for | grep -q 32bc58e6594c2ea05d314cc621472552c9f788145ee7a45e86620eeedf287199 && \
chmod 755 /bin/wait-for

RUN echo "$WORK_DIR/tests/manage.py test --no-input tests" > /bin/run-tests
RUN chmod 755 /bin/run-tests

RUN echo "$WORK_DIR/tests/manage.py runserver 0.0.0.0:80" > /bin/run-server
RUN chmod 755 /bin/run-server

COPY docker-entrypoint.sh /bin/docker-entrypoint.sh
RUN chmod 755 /bin/docker-entrypoint.sh

WORKDIR $WORK_DIR

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["run-tests"]
