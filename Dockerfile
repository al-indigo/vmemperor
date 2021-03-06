FROM ubuntu:18.04



ADD backend /app
ADD frontend /app/frontend
ADD requirements.txt /app
WORKDIR /app

ENV DOCKER True

RUN apt update && apt install -y \
    python3.7 python3.7-distutils curl wget  gdebi-core git libpng-dev build-essential
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.7

RUN pip install -r requirements.txt

RUN  apt-get update \
&&  apt-get install -y software-properties-common \
&&  apt-add-repository ppa:ansible/ansible \
&&  apt-get update \
&&  apt-get install -y ansible

RUN curl  https://deb.nodesource.com/setup_8.x | bash - && \
 apt-get install -y nodejs

WORKDIR /app
RUN ln -sf /dev/stdout nohup.out

EXPOSE 3000 8889

WORKDIR /app/frontend

RUN npm install -g pngquant-bin --allow-root  --unsafe-perm=true

RUN npm install && npm run build:dll

WORKDIR /
ADD configs/start.sh ./start.sh
CMD ./start.sh
