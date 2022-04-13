FROM golang:1.18.0-alpine3.15 as builder
COPY . /src
WORKDIR /src
RUN go build -o /git-http-proxy main.go 

FROM alpine:3.15
COPY --from=builder /git-http-proxy /git-http-proxy
USER 1000:1000
ENTRYPOINT ["/git-http-proxy"]
