FROM python:3.8.6-alpine3.12

# ==============================================================================
# 타임존 설정
RUN apk add tzdata && \
    cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone

ENV PYTHONUNBUFFERED=0

RUN apk add --no-cache --virtual .build-deps gcc musl-dev
# ==============================================================================
RUN mkdir -p /src/data-collector
ADD data_collector /src

# ==============================================================================
# 파일 복사

ADD . /src
WORKDIR /src

# ==============================================================================
# 설치
RUN python -m pip install pip --upgrade && python setup.py install

# ==============================================================================
# 설치파일 정리
WORKDIR /root
RUN rm -rf /src
RUN apk del .build-deps

EXPOSE 5000

ENTRYPOINT ["data-collector"]
