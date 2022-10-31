package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/julienschmidt/httprouter"
)

// Server represents the http server and associated components that do cachcing
// of k8s resources.
type Server struct {
	caches CacheCollection
	config Config
	router *httprouter.Router
	*http.Server
}

// LoggingResponseWriter wraps http.ResponseWriter so that it can log the http response code
// in the logs of the server.
type LoggingResponseWriter struct {
	http.ResponseWriter
	req http.Request
}

// WriteHeader wraps the original WriteHeader function of a ResponseWriter so that
// it can log the HTTP response code of requests in the log.
func (r LoggingResponseWriter) WriteHeader(status int) {
	if r.req.URL.Path != "/health" {
		// do not log requests to /health endpoint to keep logs cleaner
		log.Printf("%d %s %s %s %s", status, r.req.Method, r.req.URL.Path, r.req.Header.Get("X-Forwarded-For"), r.req.UserAgent())
	}
	r.ResponseWriter.WriteHeader(status)
}

func (s *Server) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
	var lrw = LoggingResponseWriter{rw, *req}
	s.router.ServeHTTP(lrw, req)
}

// Initialize setups the required caches and routes for the http server.
func (s *Server) Initialize(ctx context.Context) {
	log.Println("Initializing http server...")
	s.registerRoutes()
	s.Handler = s
	go s.caches.run(ctx)
	s.caches.synchronize(ctx)
}

func (s *Server) respond(w http.ResponseWriter, req *http.Request, data interface{}, err error) {
	if err != nil {
		http.Error(w, fmt.Sprintf("server error: %v", err), http.StatusInternalServerError)
		return
	}
	res, err := json.Marshal(data)
	if err != nil {
		http.Error(w, fmt.Sprintf("json encoding error: %v", err), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(res)
}

// NewServerFromConfigOrDie creates a new Server from a configuration or panics
func NewServerFromConfigOrDie(ctx context.Context, config Config) *Server {
	cacheCollection := NewCacheCollectionFromConfigOrDie(ctx, config)
	return &Server{
		config: config,
		caches: *cacheCollection,
		router: httprouter.New(),
		Server: &http.Server{
			Addr:    fmt.Sprintf(":%d", config.Port),
		},
	}
}
