# A development database for the VAST pipeline
FROM postgres:13.1

RUN apt-get update -y
RUN apt-get install -y \
  libssl-dev \
  libkrb5-dev \
  zlib1g-dev \
  make \
  git \
  gcc \
  postgresql-server-dev-13 \
  postgresql-common \
  libreadline-dev
RUN git clone -q https://github.com/segasai/q3c.git
WORKDIR /q3c
RUN make
RUN make install
