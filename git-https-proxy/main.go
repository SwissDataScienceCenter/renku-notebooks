package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"syscall"

	configLib "github.com/SwissDataScienceCenter/renku-notebooks/git-https-proxy/config"
	"github.com/SwissDataScienceCenter/renku-notebooks/git-https-proxy/proxy"
)

func main() {
	config, err := configLib.GetConfig()
	if err != nil {
		log.Fatalln(err)
	}

	if err := config.Validate(); err != nil {
		log.Fatalln(err)
	}

	if config.AnonymousSession {
		log.Println("Warning: Starting the git-proxy for an anonymous session, which is essentially useless.")
	}

	//? INFO: Make a channel that will receive the SIGTERM on shutdown
	sigTerm := make(chan os.Signal, 1)
	signal.Notify(sigTerm, syscall.SIGTERM, syscall.SIGINT)
	ctx := context.Background()

	//? INFO: Setup servers
	proxyHandler := proxy.GetProxyHandler(config)
	proxyServer := http.Server{
		Addr:    fmt.Sprintf(":%d", config.ProxyPort),
		Handler: proxyHandler,
	}
	healthHandler := getHealthHandler(config)
	healthServer := http.Server{
		Addr:    fmt.Sprintf(":%d", config.HealthPort),
		Handler: healthHandler,
	}

	//? INFO: Run servers in the background
	go func() {
		log.Printf("Health server active on port %d\n", config.HealthPort)
		log.Fatalln(healthServer.ListenAndServe())
	}()
	go func() {
		log.Printf("Git proxy active on port %d\n", config.ProxyPort)
		log.Fatalln(proxyServer.ListenAndServe())
	}()

	//? INFO: Block until you receive sigTerm to shutdown. All of this is necessary
	//? INFO: because the proxy has to shut down only after all the other containers do so in case
	//? INFO: any other containers (i.e. session or sidecar) need git right before shutting down.
	<-sigTerm
	log.Print("SIGTERM received. Shutting down servers.\n")
	err = healthServer.Shutdown(ctx)
	if err != nil {
		log.Fatalln(err)
	}
	err = proxyServer.Shutdown(ctx)
	if err != nil {
		log.Fatalln(err)
	}
}

// The proxy does not expose a health endpoint. Therefore the purpose of this server
// handler is to fill that functionality. To ensure that the proxy is fully up
// and running the health server will use the proxy as a proxy for the health endpoint.
// This is necessary because sending any requests directly to the proxy results in a 500
// with a message that the proxy only accepts proxy requests and no direct requests.
func getHealthHandler(config configLib.GitProxyConfig) *http.ServeMux {
	handler := http.NewServeMux()
	handler.HandleFunc("/ping", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		resp := make(map[string]string)
		resp["message"] = "pong"
		jsonResp, err := json.Marshal(resp)
		if err != nil {
			log.Fatalf("Error happened in JSON marshal. Err: %s", err)
		}
		w.Write(jsonResp)
	})
	handler.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		proxyUrl, err := url.Parse(fmt.Sprintf("http://localhost:%d", config.ProxyPort))
		if err != nil {
			log.Fatalln(err)
		}
		client := &http.Client{Transport: &http.Transport{Proxy: http.ProxyURL(proxyUrl)}}
		resp, err := client.Get(fmt.Sprintf("http://localhost:%d/ping", config.HealthPort))
		if err != nil {
			log.Println("The GET request to /ping from within /health failed with:", err)
			w.WriteHeader(http.StatusBadRequest)
		}
		defer resp.Body.Close()
		if resp.StatusCode >= 200 && resp.StatusCode <= 400 {
			w.WriteHeader(http.StatusOK)
		} else {
			w.WriteHeader(http.StatusBadRequest)
		}
	})
	return handler
}
