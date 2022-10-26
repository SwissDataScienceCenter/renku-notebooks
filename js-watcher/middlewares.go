package main

import (
	"log"
	"net/http"
)

func logRequests(h http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		log.Printf("%s %s %s %s", req.Method, req.URL.Path, req.Host, req.UserAgent())
		h(w, req)
	}
}
