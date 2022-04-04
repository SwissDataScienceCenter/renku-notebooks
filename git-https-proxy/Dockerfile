FROM golang:1.18.0-alpine3.15 as builder
COPY . .
RUN unset GOPATH && \
    go mod tidy && \
    go build -o /git-http-proxy main.go 

FROM golang:1.18.0-alpine3.15
COPY --from=builder /git-http-proxy /git-http-proxy
ENTRYPOINT ["/git-http-proxy"]
