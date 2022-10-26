package main

import (
	"encoding/json"
	"errors"
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

func (s *Server) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
	s.router.ServeHTTP(rw, req)
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
	var unexpectedError *UnexpectedError
	var serverError *ServerError
	if err != nil {
		if errors.As(err, &unexpectedError) {
			http.Error(w, unexpectedError.Error(), http.StatusInternalServerError)
			return
		}
		if errors.As(err, &serverError) {
			http.Error(w, serverError.Error(), http.StatusInternalServerError)
			return
		}
		http.Error(w, fmt.Sprintf("unhandled error: %v", err), http.StatusInternalServerError)
		return
	}
	if data != nil {
		w.Header().Set("Content-Type", "application/json")
		err := json.NewEncoder(w).Encode(data)
		if err != nil {
			http.Error(w, fmt.Sprintf("error building the response, %v", err), http.StatusInternalServerError)
			return
		}
	}
}