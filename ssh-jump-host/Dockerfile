FROM alpine:3.19

RUN apk add --update --no-cache openssh-server tini && \
    mkdir -p /opt/ssh && \
    adduser -D jovyan && \
    passwd -d jovyan && \
    chown -R jovyan:users /opt/ssh && \
    addgroup jovyan shadow

USER jovyan
RUN mkdir -p /opt/ssh/sshd_config.d && \
    mkdir -p /opt/ssh/ssh_host_keys && \
    ssh-keygen -q -N "" -t dsa -f /opt/ssh/ssh_host_keys/ssh_host_dsa_key && \
    ssh-keygen -q -N "" -t rsa -b 4096 -f /opt/ssh/ssh_host_keys/ssh_host_rsa_key && \
    ssh-keygen -q -N "" -t ecdsa -f /opt/ssh/ssh_host_keys/ssh_host_ecdsa_key && \
    ssh-keygen -q -N "" -t ed25519 -f /opt/ssh/ssh_host_keys/ssh_host_ed25519_key
COPY sshd_config /opt/ssh/sshd_config
ENTRYPOINT ["tini", "-g", "--"]
CMD [ "/usr/sbin/sshd", "-D", "-f", "/opt/ssh/sshd_config", "-e" ]
