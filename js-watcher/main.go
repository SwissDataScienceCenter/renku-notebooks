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
	
	config, err := NewConfigFromEnv("")
	if err != nil {
		log.Fatalf("Cannot setup config: %s\n", err.Error())
	}
	log.Printf("Running with config %+v\n", config)
	cacheCollection, err := NewCacheCollectionFromConfig(ctx, config)
	if err != nil {
		log.Fatalf("Cannot initialize cache collection: %s\n", err.Error())
	}
	aServer := Server{
		config: config,
		caches: *cacheCollection,
		router: httprouter.New(),
	}
	go aServer.caches.run(ctx)
	aServer.caches.synchronize(ctx)
	log.Println("Setting up routes")
	aServer.routes()
	aServer.setup()
	log.Println("Starting server...")
	go func () {
		<- stopCh
		log.Println("Received shutdown signal")
		log.Println("Shutting down server gracefully")
		err := aServer.server.Shutdown(ctx)
		if err != nil {
			log.Printf("Graceful server shutdown failed: %v\n", err)
		}
		cancel()
	}()
	aServer.start()
}
