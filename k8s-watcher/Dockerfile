FROM golang:1.21-alpine3.20 as builder
COPY . /src
WORKDIR /src
RUN go build -o /k8s-watcher

FROM alpine:3.20
COPY --from=builder /k8s-watcher /k8s-watcher
USER 1000:1000
ENTRYPOINT ["/k8s-watcher"]
