FROM python:3.12-alpine

RUN apk add socat && pip install poetry

ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app
COPY . .
RUN poetry install

CMD ["sh", "./docker-entrypoint.sh", "python", "-m", "i4a_ui"]
