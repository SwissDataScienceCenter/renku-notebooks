package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/julienschmidt/httprouter"
)

type Server struct {
	caches CacheCollection
	config Config
	router *httprouter.Router
	server *http.Server
}

type LoggingResponseWriter struct {
	http.ResponseWriter
	req http.Request
}

func (r LoggingResponseWriter) WriteHeader(status int) {
	if r.req.URL.Path != "/health" {
		// do not log requests to /health endpoint to keep logs cleaner
		log.Printf("%d %s %s %s %s", status, r.req.Method, r.req.URL.Path, r.req.Header.Get("X-Forwarded-For"), r.req.UserAgent())
	}
	r.ResponseWriter.WriteHeader(status)
}

func (s *Server) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
	var lrw LoggingResponseWriter = LoggingResponseWriter{rw, *req}
	s.router.ServeHTTP(lrw, req)
}

func (s *Server) setup() {
	s.server = &http.Server{
		Addr: fmt.Sprintf(":%d", s.config.Port),
		Handler: s,
	}
}

func (s *Server) start() {
	log.Fatal(s.server.ListenAndServe())
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
