ARG UBUNTU_VERSION=22.04
FROM ubuntu:${UBUNTU_VERSION} AS base

# OS dependencies and packages
RUN apt-get update && \
    apt-get install nginx --no-install-recommends -y \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 80
WORKDIR /var/www/html

COPY index.html /var/www/html/index.html

CMD [ "nginx", "-g", "daemon off;" ]
