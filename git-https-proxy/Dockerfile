FROM golang:1.19.3-alpine3.16 as builder
COPY . /src
WORKDIR /src
RUN go build -o /git-http-proxy

FROM alpine:3
COPY --from=builder /git-http-proxy /git-http-proxy

USER 1000:1000
ENTRYPOINT ["/git-http-proxy"]
