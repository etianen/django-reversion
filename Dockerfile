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

RUN echo "$WORK_DIR/tests/manage.py test tests" > /bin/run-tests
RUN chmod 755 /bin/run-tests

COPY . $WORK_DIR
WORKDIR $WORK_DIR

RUN pip install -e .

CMD run-tests
