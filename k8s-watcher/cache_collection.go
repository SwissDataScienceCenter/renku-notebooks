package main

import (
	"context"
	"log"
	"time"

	k8sErrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
)

// CacheCollection is a map that hold caches for different namespaces.
// The keys of the cache represent different k8s namespaces.
type CacheCollection map[string]*Cache

// synchronize waits until the k8s informer cache is fully synced with the cluster.
// If mutliple namespaces are cached then it will sync the namespaces in parallel.
func (c CacheCollection) synchronize(ctx context.Context, timeout time.Duration) {
	doneCh := make(chan bool)
	timeoutCh := make(chan bool)
	// timeout cache sync after a sepcified duration
	go func() {
		time.Sleep(timeout)
		timeoutCh <- true
	}()
	for namespace, cache := range c {
		log.Printf("Starting sync for %s\n", namespace)
		go cache.synchronize(ctx, doneCh)
	}
	syncCount := 0
	log.Println("Waiting on cache synchronization")
	for {
		if syncCount == len(c) {
			break
		}
		select {
		case cacheSyncOK := <-doneCh:
			if !cacheSyncOK {
				log.Fatalf("Failed to sync cache\n")
			}
			syncCount++
			log.Printf("Synced %d/%d caches\n", syncCount, len(c))
		case <-timeoutCh:
			log.Fatalf("Syncing caches timed out after %.f seconds\n.", timeout.Seconds())
		}
	}
	log.Println("Synced all caches!")
}

// run runs the k8s informers for each namespace in parallel.
func (c CacheCollection) run(ctx context.Context) {
	for namespace, cache := range c {
		log.Printf("Starting cache for %s\n", namespace)
		go cache.run(ctx)
	}
}

// getAll returns all resources that that are cached in the informer.
func (c CacheCollection) getAll() (res []runtime.Object, err error) {
	// if not initialized to empty slice then the api return null instead of [], but we want to return []
	res = []runtime.Object{}
	var ires []runtime.Object
	for _, cache := range c {
		ires, err = cache.getAll()
		if err != nil {
			return
		}
		res = append(res, ires...)
	}
	return
}

// getByUserID returns all resources that that are cached in the informer
// and have a label whose name is pre-defined in the config and whose value is
// passed as an argument.
func (c CacheCollection) getByUserID(userID string) (res []runtime.Object, err error) {
	// if not initialized to empty slice then the api return null instead of [], but we want to return []
	res = []runtime.Object{}
	var ires []runtime.Object
	for _, cache := range c {
		ires, err = cache.getByUserID(userID)
		if err != nil {
			return
		}
		res = append(res, ires...)
	}
	return
}

// getByNameAndUserID looks for a specific resource (by its name) that belongs to
// a specific user.
func (c CacheCollection) getByNameAndUserID(name string, userID string) (res []runtime.Object, err error) {
	// if not initialized to empty slice then the api return null instead of [], but we want to return []
	res = []runtime.Object{}
	var ires runtime.Object
	for _, cache := range c {
		ires, err = cache.getByNameAndUserID(name, userID)
		if err != nil {
			if k8sErrors.IsNotFound(err) {
				// The server watcher does not send 404 on requesting a missing k8s custom resource,
				// so in this case we simply keep looking through all the caches to see if the requested
				// resource exists anywhere. If the resource is not found the server reponds with an empty list.
				continue
			}
			return
		}
		if ires != nil {
			res = append(res, ires)
		}
	}
	return res, nil
}

// getByName looks for a specifc resource in the cache only by the name of the resource
// without any other filter or matching crteria.
func (c CacheCollection) getByName(name string) (res []runtime.Object, err error) {
	// if not initialized to empty slice then the api return null instead of [], but we want to return []
	res = []runtime.Object{}
	var ires runtime.Object
	for _, cache := range c {
		ires, err = cache.getByName(name)
		if err != nil {
			if k8sErrors.IsNotFound(err) {
				// The server watcher does not send 404 on requesting a missing k8s custom resource,
				// so in this case we simply keep looking through all the caches to see if the requested
				// resource exists anywhere. If the resource is not found the server reponds with an empty list.
				continue
			}
			return
		}
		if ires != nil {
			res = append(res, ires)
		}
	}
	return res, nil
}

// NewJupyterServerCacheCollectionFromConfigOrDie generates a new cache map from a configuration. If it cannot
// do this successfully it will terminate the program because the server cannot run at all if this
// step fails in any way and the program cannot recover from errors that occur here.
func NewJupyterServerCacheCollectionFromConfigOrDie(ctx context.Context, config Config) *CacheCollection {
	caches := CacheCollection{}
	for _, namespace := range config.Namespaces {
		cache, err := NewJupyterServerCacheFromConfig(ctx, config, namespace)
		if err != nil {
			log.Fatalf("Cannot create cache collection: %v\n", err)
		}
		caches[namespace] = cache
	}
	return &caches
}

// NewAmaltheaSessionCacheCollectionFromConfigOrDie generates a new cache map from a configuration. If it cannot
// do this successfully it will terminate the program because the server cannot run at all if this
// step fails in any way and the program cannot recover from errors that occur here.
func NewAmaltheaSessionCacheCollectionFromConfigOrDie(ctx context.Context, config Config) *CacheCollection {
	caches := CacheCollection{}
	for _, namespace := range config.Namespaces {
		cache, err := NewAmaltheaSessionCacheFromConfig(ctx, config, namespace)
		if err != nil {
			log.Fatalf("Cannot create cache collection: %v\n", err)
		}
		caches[namespace] = cache
	}
	return &caches
}

// NewShipwrightBuildRunCacheCollectionFromConfigOrDie generates a new cache map from a configuration. If it cannot
// do this successfully it will terminate the program because the server cannot run at all if this
// step fails in any way and the program cannot recover from errors that occur here.
func NewShipwrightBuildRunCacheCollectionFromConfigOrDie(ctx context.Context, config Config) *CacheCollection {
	caches := CacheCollection{}
	for _, namespace := range config.Namespaces {
		cache, err := NewShipwrightBuildRunCacheFromConfig(ctx, config, namespace)
		if err != nil {
			log.Fatalf("Cannot create cache collection: %v\n", err)
		}
		caches[namespace] = cache
	}
	return &caches
}

// NewShipwrightBuildCacheCollectionFromConfigOrDie generates a new cache map from a configuration. If it cannot
// do this successfully it will terminate the program because the server cannot run at all if this
// step fails in any way and the program cannot recover from errors that occur here.
func NewShipwrightBuildCacheCollectionFromConfigOrDie(ctx context.Context, config Config) *CacheCollection {
	caches := CacheCollection{}
	for _, namespace := range config.Namespaces {
		cache, err := NewShipwrightBuildCacheFromConfig(ctx, config, namespace)
		if err != nil {
			log.Fatalf("Cannot create cache collection: %v\n", err)
		}
		caches[namespace] = cache
	}
	return &caches
}
