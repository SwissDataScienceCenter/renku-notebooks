package main

import (
	"net/http"

	"github.com/julienschmidt/httprouter"
)

// routers registers the handlers for all http endpoints the server supports.
func (s *Server) registerRoutes() {
	s.router.HandlerFunc("GET", "/servers", s.handleIndex())
	s.router.HandlerFunc("GET", "/servers/:serverID", s.handleServerID())
	s.router.HandlerFunc("GET", "/users/:userID/servers", s.handleUserID())
	s.router.HandlerFunc("GET", "/users/:userID/servers/:serverID", s.handleUserIDServerID())
	s.router.HandlerFunc("GET", "/health", s.handleHealthCheck())
}

func (s *Server) handleIndex() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		output, err := s.caches.getAll()
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleServerID() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		params := httprouter.ParamsFromContext(req.Context())
		output, err := s.caches.getByName(params.ByName("serverID"))
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleUserID() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		params := httprouter.ParamsFromContext(req.Context())
		output, err := s.caches.getByUserID(params.ByName("userID"))
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleUserIDServerID() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		params := httprouter.ParamsFromContext(req.Context())
		output, err := s.caches.getByNameAndUserID(params.ByName("serverID"), params.ByName("userID"))
		s.respond(w, req, output, err)
	}
}

func (s *Server) handleHealthCheck() http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		s.respond(w, req, map[string]string{"running": "ok"}, nil)
	}
}
