package main

import (
	"net/http"

	"github.com/julienschmidt/httprouter"
)

// routers registers the handlers for all http endpoints the server supports.
func (s *Server) registerRoutes() {
	s.router.HandlerFunc("GET", "/health", s.handleHealthCheck)
	// Used for the old amalthea operator in charge of jupyterservers custom resources
	s.router.HandlerFunc("GET", "/servers", s.jsGetAll)
	s.router.HandlerFunc("GET", "/servers/:serverID", s.jsGetOne)
	s.router.HandlerFunc("GET", "/users/:userID/servers", s.jsUserID)
	s.router.HandlerFunc("GET", "/users/:userID/servers/:serverID", s.jsUserIDServerID)
	// Used for the new amalthea operator in charge of amaltheasessions custom resources
	s.router.HandlerFunc("GET", "/sessions", s.asGetAll)
	s.router.HandlerFunc("GET", "/sessions/:serverID", s.asGetOne)
	s.router.HandlerFunc("GET", "/users/:userID/sessions", s.asUserID)
	s.router.HandlerFunc("GET", "/users/:userID/sessions/:serverID", s.asUserIDServerID)
	// Used for the shipwright operator in charge of image build custom resources
	s.router.HandlerFunc("GET", "/buildruns", s.brGetAll)
	s.router.HandlerFunc("GET", "/buildruns/:buildRunID", s.brGetOne)
	// Used for the shipwright operator in charge of image build custom resources
	s.router.HandlerFunc("GET", "/taskruns", s.trGetAll)
	s.router.HandlerFunc("GET", "/taskruns/:taskRunID", s.trGetOne)
}

func (s *Server) jsGetAll(w http.ResponseWriter, req *http.Request) {
	output, err := s.cachesJS.getAll()
	s.respond(w, req, output, err)
}

func (s *Server) jsGetOne(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesJS.getByName(params.ByName("serverID"))
	s.respond(w, req, output, err)
}

func (s *Server) jsUserID(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesJS.getByUserID(params.ByName("userID"))
	s.respond(w, req, output, err)
}

func (s *Server) jsUserIDServerID(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesJS.getByNameAndUserID(params.ByName("serverID"), params.ByName("userID"))
	s.respond(w, req, output, err)
}

func (s *Server) asGetAll(w http.ResponseWriter, req *http.Request) {
	output, err := s.cachesAS.getAll()
	s.respond(w, req, output, err)
}

func (s *Server) asGetOne(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesAS.getByName(params.ByName("serverID"))
	s.respond(w, req, output, err)
}

func (s *Server) asUserID(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesAS.getByUserID(params.ByName("userID"))
	s.respond(w, req, output, err)
}

func (s *Server) asUserIDServerID(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesAS.getByNameAndUserID(params.ByName("serverID"), params.ByName("userID"))
	s.respond(w, req, output, err)
}

func (s *Server) brGetAll(w http.ResponseWriter, req *http.Request) {
	output, err := s.cachesBR.getAll()
	s.respond(w, req, output, err)
}

func (s *Server) brGetOne(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesBR.getByName(params.ByName("buildRunID"))
	s.respond(w, req, output, err)
}

func (s *Server) trGetAll(w http.ResponseWriter, req *http.Request) {
	output, err := s.cachesTR.getAll()
	s.respond(w, req, output, err)
}

func (s *Server) trGetOne(w http.ResponseWriter, req *http.Request) {
	params := httprouter.ParamsFromContext(req.Context())
	output, err := s.cachesTR.getByName(params.ByName("taskRunID"))
	s.respond(w, req, output, err)
}

func (s *Server) handleHealthCheck(w http.ResponseWriter, req *http.Request) {
	s.respond(w, req, map[string]string{"running": "ok"}, nil)
}
