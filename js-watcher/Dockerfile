FROM golang:1.19.0-alpine3.16 as builder
COPY . /src
WORKDIR /src
RUN go build -o /js-watcher

FROM alpine:3.16
COPY --from=builder /js-watcher /js-watcher
USER 1000:1000
ENTRYPOINT ["/js-watcher"]
