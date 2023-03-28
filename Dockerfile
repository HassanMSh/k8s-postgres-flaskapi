FROM python:3.8-alpine

RUN apk update && apk upgrade && apk add \
        nginx \
        python3-dev \
        build-base \
        libffi-dev \
        openssl-dev \
        linux-headers \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt --src /usr/local/src

COPY . .

EXPOSE 5000
CMD [ "python", "flaskapi.py" ]
