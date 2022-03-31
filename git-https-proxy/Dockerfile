# Copied from https://hub.docker.com/r/bitnami/nginx
# Recommeneded way by bitnami to recompile nginx with custom modules
# The module is tied to nginx 1.21.1 and changing the ARG below also requires manual changes 
# further in the dockerfile for what module is downloaded from the git repository
ARG NGINX_VERSION=1.21.1
ARG BITNAMI_NGINX_REVISION=r51
ARG BITNAMI_NGINX_TAG=${NGINX_VERSION}-debian-10-${BITNAMI_NGINX_REVISION}

FROM bitnami/nginx:${BITNAMI_NGINX_TAG} AS builder
USER root
## Redeclare NGINX_VERSION so it can be used as a parameter inside this build stage
ARG NGINX_VERSION
## Install required packages and build dependencies
RUN install_packages dirmngr gpg gpg-agent curl build-essential libpcre3-dev zlib1g-dev libperl-dev unzip patch
## Download the module
ADD https://github.com/chobits/ngx_http_proxy_connect_module/archive/6dce7204426255f3fde5ec7a71a43454c6e9ca84.zip \
    http://nginx.org/keys/nginx_signing.key \
    /tmp/
## Download NGINX, verify integrity and extract
RUN cd /tmp && \
    curl -O http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
    curl -O http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz.asc && \
    tar xzf nginx-${NGINX_VERSION}.tar.gz && \
    unzip 6dce7204426255f3fde5ec7a71a43454c6e9ca84.zip && \
    mv ngx_http_proxy_connect_module-6dce7204426255f3fde5ec7a71a43454c6e9ca84 ngx_http_proxy_connect_module && \
    mv ngx_http_proxy_connect_module /
## Compile NGINX with desired module
RUN cd /tmp/nginx-${NGINX_VERSION} && \
    rm -rf /opt/bitnami/nginx && \
    patch -p1 < /ngx_http_proxy_connect_module/patch/proxy_connect_rewrite_102101.patch && \
    ./configure --prefix=/opt/bitnami/nginx --with-compat --add-dynamic-module=/ngx_http_proxy_connect_module && \
    make && \
    make install

FROM bitnami/nginx:${BITNAMI_NGINX_TAG}
USER root
COPY --from=builder /opt/bitnami/nginx/modules/ngx_http_proxy_connect_module.so /opt/bitnami/nginx/modules/ngx_http_proxy_connect_module.so
## Enable module
RUN echo "load_module /opt/bitnami/nginx/modules/ngx_http_proxy_connect_module.so;" | cat - /opt/bitnami/nginx/conf/nginx.conf > /tmp/nginx.conf && \
    sed -i 's/http {/http {\n    variables_hash_max_size 2048;\n    variables_hash_bucket_size 128;/' /tmp/nginx.conf && \
    head -45 /tmp/nginx.conf > /tmp/nginx_final.conf && \
    echo "\n}\n" >> /tmp/nginx_final.conf && \
    cp /tmp/nginx_final.conf /opt/bitnami/nginx/conf/nginx.conf
## Set the container to be run as a non-root user by default
USER 1001
