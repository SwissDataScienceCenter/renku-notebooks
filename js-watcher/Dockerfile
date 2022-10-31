FROM golang:1.19.0-alpine3.16 as builder
COPY . /src
WORKDIR /src
RUN go build -o /k8s-watcher

FROM alpine:3.16
COPY --from=builder /k8s-watcher /k8s-watcher
USER 1000:1000
ENTRYPOINT ["/k8s-watcher"]
