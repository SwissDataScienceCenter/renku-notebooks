package main

import (
	"net/http"

	"github.com/julienschmidt/httprouter"
)

func (s *Server) routes() {
	s.router.HandlerFunc("GET", "/servers", logRequests(s.handleIndex()))
	s.router.HandlerFunc("GET", "/servers/:serverId", logRequests(s.handleServerId()))
	s.router.HandlerFunc("GET", "/users/:userId/servers", logRequests(s.handleUserId()))
	s.router.HandlerFunc("GET", "/users/:userId/servers/:serverId", logRequests(s.handleUserIdServerId()))
	// Do not log /health requests to avoid polluting logs
	s.router.HandlerFunc("GET", "/health", s.handleHealthCheck())
}

func (s *Server) handleIndex() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		output, err := s.caches.getAll()
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleServerId() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		params := httprouter.ParamsFromContext(req.Context())
		output, err := s.caches.getByName(params.ByName("serverId"))
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleUserId() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		params := httprouter.ParamsFromContext(req.Context())
		output, err := s.caches.getByUserId(params.ByName("userId"))
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleUserIdServerId() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		params := httprouter.ParamsFromContext(req.Context())
		output, err := s.caches.getByNameAndUserId(params.ByName("serverId"), params.ByName("userId"))
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleHealthCheck() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		s.respond(w, req, map[string]string{"running": "ok"}, nil)
	}
}

