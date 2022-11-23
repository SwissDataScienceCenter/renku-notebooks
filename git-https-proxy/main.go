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
	"regexp"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/SwissDataScienceCenter/renku-notebooks/git-https-proxy/config"
	configLib "github.com/SwissDataScienceCenter/renku-notebooks/git-https-proxy/config"
	"github.com/elazarl/goproxy"
)

func main() {
	config := configLib.ParseEnv()
	// INFO: Make a channel that will receive the SIGTERM on shutdown
	sigTerm := make(chan os.Signal, 1)
	signal.Notify(sigTerm, syscall.SIGTERM, syscall.SIGINT)
	ctx := context.Background()
	// INFO: Used to coordinate shutdown between git-proxy and the session when the user
	// is not anonymous and there may be an autosave branch that needs to be created
	shutdownFlags := shutdownFlagsStruct{
		sigtermReceived: false,
		shutdownAllowed: false,
	}

	// INFO: Setup servers
	proxyHandler := getProxyHandler(config)
	proxyServer := http.Server{
		Addr:    fmt.Sprintf(":%s", config.ProxyPort),
		Handler: proxyHandler,
	}
	healthHandler := getHealthHandler(config, &shutdownFlags)
	healthServer := http.Server{
		Addr:    fmt.Sprintf(":%s", config.HealthPort),
		Handler: healthHandler,
	}

	// INFO: Run servers in the background
	go func() {
		log.Printf("Health server active on port %s\n", config.HealthPort)
		log.Fatalln(healthServer.ListenAndServe())
	}()
	go func() {
		log.Printf("Git proxy active on port %s\n", config.ProxyPort)
		log.Printf("Repo Url: %v, anonymous session: %v\n", config.RepoURL, config.AnonymousSession)
		log.Fatalln(proxyServer.ListenAndServe())
	}()

	// INFO: Block until you receive sigTerm to shutdown. All of this is necessary
	// because the proxy has to shut down only after all the other containers do so in case
	// any other containers (i.e. session or sidecar) need git right before shutting down,
	// and this is the case exactly for creating autosave branches.
	<-sigTerm
	if config.AnonymousSession {
		log.Print("SIGTERM received. Shutting down servers.\n")
		healthServer.Shutdown(ctx)
		proxyServer.Shutdown(ctx)
	} else {
		log.Printf(
			"SIGTERM received. Waiting for /shutdown to be called or timing out in %v\n",
			config.SessionTerminationGracePeriod,
		)
		sigTermTime := time.Now()
		shutdownFlags.lock.Lock()
		shutdownFlags.sigtermReceived = true
		shutdownFlags.lock.Unlock()
		for {
			if shutdownFlags.shutdownAllowed || (time.Now().Sub(sigTermTime) > config.SessionTerminationGracePeriod) {
				log.Printf(
					"Shutting down servers. SIGTERM received: %v, Shutdown allowed: %v.\n",
					shutdownFlags.sigtermReceived,
					shutdownFlags.shutdownAllowed,
				)
				err := healthServer.Shutdown(ctx)
				if err != nil {
					log.Fatalln(err)
				}
				err = proxyServer.Shutdown(ctx)
				if err != nil {
					log.Fatalln(err)
				}
				break
			}
			time.Sleep(time.Second * 5)
		}
	}
}

type shutdownFlagsStruct struct {
	sigtermReceived bool
	shutdownAllowed bool
	lock            sync.Mutex
}

// Infer port if not explicitly specified
func getPort(urlAddress *url.URL) string {
	if urlAddress.Port() == "" {
		if urlAddress.Scheme == "http" {
			return "80"
		} else if urlAddress.Scheme == "https" {
			return "443"
		}
	}
	return urlAddress.Port()
}

// Ensure that hosts name watch with/without. I.e.
// ensure www.hostname.com matches hostname.com and vice versa
func hostsMatch(url1 *url.URL, url2 *url.URL) bool {
	var err error
	var url1ContainsWww, url2ContainsWww bool
	wwwRegex := fmt.Sprintf("^%s", regexp.QuoteMeta("www."))
	url1ContainsWww, err = regexp.MatchString(wwwRegex, url1.Hostname())
	if err != nil {
		log.Fatalln(err)
	}
	url2ContainsWww, err = regexp.MatchString(wwwRegex, url2.Hostname())
	if err != nil {
		log.Fatalln(err)
	}
	if url1ContainsWww && !url2ContainsWww {
		return url1.Hostname() == fmt.Sprintf("www.%s", url2.Hostname())
	} else if !url1ContainsWww && url2ContainsWww {
		return fmt.Sprintf("www.%s", url1.Hostname()) == url2.Hostname()
	} else {
		return url1.Hostname() == url2.Hostname()
	}
}

// Return a server handler that contains the proxy that injects the Git aithorization header when
// the conditions for doing so are met.
func getProxyHandler(config configLib.GitProxyConfig) *goproxy.ProxyHttpServer {
	proxyHandler := goproxy.NewProxyHttpServer()
	proxyHandler.Verbose = false
	gitRepoHostWithWww := fmt.Sprintf("www.%s", config.RepoURL.Hostname())
	handlerFunc := func(r *http.Request, ctx *goproxy.ProxyCtx) (*http.Request, *http.Response) {
		var validGitRequest bool
		validGitRequest = r.URL.Scheme == config.RepoURL.Scheme &&
			hostsMatch(r.URL, config.RepoURL) &&
			getPort(r.URL) == getPort(config.RepoURL) &&
			strings.HasPrefix(strings.TrimLeft(r.URL.Path, "/"), strings.TrimLeft(config.RepoURL.Path, "/"))
		if config.AnonymousSession {
			log.Print("Anonymous session, not adding auth headers, letting request through without adding auth headers.\n")
			return r, nil
		}
		if !validGitRequest {
			log.Printf("The request %s does not match the git repository %s letting request through without adding auth headers\n", r.URL.String(), config.RepoURL.String())
			return r, nil
		}
		log.Printf("The request %s matches the git repository %s, adding auth headers\n", r.URL.String(), config.RepoURL.String())
		gitToken, err := config.GetGitOauthToken(true)
		if err != nil {
			log.Printf("The git token cannot be refreshed, returning 401, error: %s\n", err.Error())
			return r, goproxy.NewResponse(r, goproxy.ContentTypeText, 401, "The git token could not be refreshed")
		}
		r.Header.Set("Authorization", fmt.Sprintf("Basic %s", gitToken))
		return r, nil
	}
	// NOTE: We need to eavesdrop on the HTTPS connection to insert the Auth header
	// we do this only for the case where the request host matches the host of the git repo
	// in all other cases we leave the request alone.
	proxyHandler.OnRequest(goproxy.ReqHostIs(
		config.RepoURL.Hostname(),
		gitRepoHostWithWww,
		fmt.Sprintf("%s:443", config.RepoURL.Hostname()),
		fmt.Sprintf("%s:443", gitRepoHostWithWww),
	)).HandleConnect(goproxy.AlwaysMitm)
	proxyHandler.OnRequest().DoFunc(handlerFunc)
	return proxyHandler
}

// The proxy does not expose a health endpoint. Therefore the purpose of this server
// handler is to fill that functionality. To ensure that the proxy is fully up
// and running the health server will use the proxy as a proxy for the health endpoint.
// This is necessary because sending any requests directly to the proxy results in a 500
// with a message that the proxy only accepts proxy requests and no direct requests.
// In addition this server also handles the shutdown of the git proxy. This is necessary because
// k8s does not enforce a shutdown order for containers. But we need the git proxy to wait on the
// autosave creation to finish before it shuts down. Otherwise once the session is shut down
// in many cases the git proxy shutsdown quickly before the session and autosave creation fails.
func getHealthHandler(config config.GitProxyConfig, shutdownFlags *shutdownFlagsStruct) *http.ServeMux {
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
		proxyUrl, err := url.Parse(fmt.Sprintf("http://localhost:%s", config.ProxyPort))
		if err != nil {
			log.Fatalln(err)
		}
		client := &http.Client{Transport: &http.Transport{Proxy: http.ProxyURL(proxyUrl)}}
		resp, err := client.Get(fmt.Sprintf("http://localhost:%s/ping", config.HealthPort))
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
	handler.HandleFunc("/shutdown", func(w http.ResponseWriter, r *http.Request) {
		if !shutdownFlags.sigtermReceived {
			// INFO: Cannot shut down yet
			w.WriteHeader(http.StatusConflict)
		} else {
			// INFO: Ok to shut down
			shutdownFlags.lock.Lock()
			defer shutdownFlags.lock.Unlock()
			w.WriteHeader(http.StatusOK)
			shutdownFlags.shutdownAllowed = true
		}
	})
	return handler
}
