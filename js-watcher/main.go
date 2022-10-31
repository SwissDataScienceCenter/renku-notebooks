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

	"github.com/julienschmidt/httprouter"
)

func main() {
	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	stopCh := make(chan os.Signal, 1)
	signal.Notify(stopCh, syscall.SIGTERM, os.Interrupt)

	config := NewConfigFromEnvOrDie("JS_CACHE_")
	log.Printf("Running with config %+v\n", config)
	cacheCollection := NewCacheCollectionFromConfigOrDie(ctx, config)
	aServer := Server{
		config: config,
		caches: *cacheCollection,
		router: httprouter.New(),
	}
	go func() {
		<-stopCh
		log.Println("Received shutdown signal")
		log.Println("Shutting down server gracefully")
		err := aServer.server.Shutdown(ctx)
		if err != nil {
			log.Printf("Graceful server shutdown failed: %v\n", err)
		}
		cancel()
	}()
	go aServer.caches.run(ctx)
	aServer.caches.synchronize(ctx)
	log.Println("Setting up routes")
	aServer.routes()
	aServer.setup()
	log.Println("Starting server...")
	aServer.start()
}
