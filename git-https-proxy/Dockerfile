FROM nginx:1.21.1-alpine AS builder
ADD https://github.com/chobits/ngx_http_proxy_connect_module/archive/6dce7204426255f3fde5ec7a71a43454c6e9ca84.zip \
    http://nginx.org/download/nginx-1.21.1.tar.gz \
    /tmp/
RUN apk add unzip build-base pcre-dev perl-dev zlib-dev openssl-dev linux-headers && \
    cd /tmp && \
    tar xzf nginx-1.21.1.tar.gz && \
    unzip 6dce7204426255f3fde5ec7a71a43454c6e9ca84.zip && \
    mv ngx_http_proxy_connect_module-6dce7204426255f3fde5ec7a71a43454c6e9ca84 ngx_http_proxy_connect_module && \
    mv ngx_http_proxy_connect_module / && \
    cd /tmp/nginx-1.21.1 && \
    patch -p1 < /ngx_http_proxy_connect_module/patch/proxy_connect_rewrite_102101.patch && \
    ./configure --add-dynamic-module=/ngx_http_proxy_connect_module --prefix=/etc/nginx --sbin-path=/usr/sbin/nginx --modules-path=/usr/lib/nginx/modules --conf-path=/etc/nginx/nginx.conf --error-log-path=/var/log/nginx/error.log --http-log-path=/var/log/nginx/access.log --pid-path=/var/run/nginx.pid --lock-path=/var/run/nginx.lock --http-client-body-temp-path=/var/cache/nginx/client_temp --http-proxy-temp-path=/var/cache/nginx/proxy_temp --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp --http-scgi-temp-path=/var/cache/nginx/scgi_temp --with-perl_modules_path=/usr/lib/perl5/vendor_perl --user=nginx --group=nginx --with-compat --with-file-aio --with-threads --with-http_addition_module --with-http_auth_request_module --with-http_dav_module --with-http_flv_module --with-http_gunzip_module --with-http_gzip_static_module --with-http_mp4_module --with-http_random_index_module --with-http_realip_module --with-http_secure_link_module --with-http_slice_module --with-http_ssl_module --with-http_stub_status_module --with-http_sub_module --with-http_v2_module --with-mail --with-mail_ssl_module --with-stream --with-stream_realip_module --with-stream_ssl_module --with-stream_ssl_preread_module --with-cc-opt='-Os -fomit-frame-pointer -g' --with-ld-opt=-Wl,--as-needed,-O1,--sort-common && \
    make && \
    make modules && \
    make install

FROM nginx:1.21.1-alpine
COPY --from=builder /etc/nginx /etc/nginx
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
COPY --from=builder /usr/lib/nginx/modules /usr/lib/nginx/modules
RUN echo "load_module modules/ngx_http_proxy_connect_module.so;" | cat - /etc/nginx/nginx.conf > /tmp/nginx.conf && \
    cp /tmp/nginx.conf /etc/nginx/nginx.conf
