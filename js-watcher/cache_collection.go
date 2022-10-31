package main

import (
	"context"
	"log"

	"k8s.io/apimachinery/pkg/runtime"
)

// CacheCollection is a map that hold caches for different namespaces.
// The keys of the cache represent different k8s namespaces.
type CacheCollection map[string]*Cache

func (c *CacheCollection) synchronize(ctx context.Context) {
	doneCh := make(chan bool)
	for namespace, cache := range *c {
		log.Printf("Starting sync for %s\n", namespace)
		go cache.synchronize(ctx, doneCh)
	}
	syncCount := 0
	log.Println("Waiting on cache synchronization")
	for {
		cacheSyncOK := <-doneCh
		if !cacheSyncOK {
			log.Fatalf("Failed to sync cache\n")
		}
		syncCount++
		log.Printf("Synced %d/%d caches\n", syncCount, len(*c))
		if syncCount == len(*c) {
			break
		}
	}
	log.Println("Synced all caches!")
}

func (c *CacheCollection) run(ctx context.Context) {
	for namespace, cache := range *c {
		log.Printf("Starting cache for %s\n", namespace)
		go cache.run(ctx)
	}
}

func (c *CacheCollection) getAll() ([]runtime.Object, error) {
	output := []runtime.Object{}
	for _, cache := range *c {
		res, err := cache.getAll()
		if err != nil {
			return nil, err
		}
		output = append(output, res...)
	}
	return output, nil
}

func (c *CacheCollection) getByUserID(userID string) ([]runtime.Object, error) {
	output := []runtime.Object{}
	for _, cache := range *c {
		res, err := cache.getByUserID(userID)
		if err != nil {
			return nil, err
		}
		output = append(output, res...)
	}
	return output, nil
}

func (c *CacheCollection) getByNameAndUserID(name string, userID string) ([]runtime.Object, error) {
	output := []runtime.Object{}
	for _, cache := range *c {
		res, err := cache.getByNameAndUserID(name, userID)
		if err != nil {
			continue
		}
		if res != nil {
			output = append(output, res)
		}
	}
	return output, nil
}

func (c *CacheCollection) getByName(name string) ([]runtime.Object, error) {
	output := []runtime.Object{}
	for _, cache := range *c {
		res, err := cache.getByName(name)
		if err != nil {
			continue
		}
		if res != nil {
			output = append(output, res)
		}
	}
	return output, nil
}

// NewCacheCollectionFromConfigOrDie generates a new cache map from a configuration. If it cannot
// do this successfully it will terminate the program because the server cannot run at all if this
// step fails in any way and the program cannot recover from errors that occur here.
func NewCacheCollectionFromConfigOrDie(ctx context.Context, config Config) *CacheCollection {
	caches := CacheCollection{}
	for _, namespace := range config.Namespaces {
		cache, err := NewCacheFromConfig(ctx, config, namespace)
		if err != nil {
			log.Fatalf("Cannot create cache collection: %v\n", err)
		}
		caches[namespace] = cache
	}
	return &caches
}
