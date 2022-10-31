FROM golang:1.19.0-alpine3.16 as builder
COPY . /src
WORKDIR /src
RUN go build -o /server-watcher

FROM alpine:3.16
COPY --from=builder /server-watcher /server-watcher
USER 1000:1000
ENTRYPOINT ["/server-watcher"]
