// A simple http server that caches k8s resources and provides endpoints
// used to list or filter the cached resources. Internally user the golang
// k8s client informer for this purpose.
package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	stopCh := make(chan os.Signal, 1)
	signal.Notify(stopCh, syscall.SIGTERM, os.Interrupt)

	config := NewConfigFromEnvOrDie("K8S_WATCHER_")
	log.Printf("Running with config %+v\n", config)
	aServer := NewServerFromConfigOrDie(ctx, config)
	go func() {
		<-stopCh
		log.Println("Received shutdown signal")
		err := aServer.Shutdown(ctx)
		if err != nil {
			log.Printf("Graceful server shutdown failed: %v\n", err)
		}
		cancel()
	}()
	aServer.Initialize(ctx)
	log.Printf("Starting http server on port %d...\n", aServer.config.Port)
	aServer.ListenAndServe()
}
