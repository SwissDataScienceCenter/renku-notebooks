package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"

	"github.com/elazarl/goproxy"
)

func main() {
	config := parseEnv()
	proxyHandler := getProxyHandler(config)
	proxyServer := http.Server{
		Addr:    fmt.Sprintf("0.0.0.0:%s", config.ProxyPort),
		Handler: proxyHandler,
	}
	healthHandler := getHealthHandler(config)
	healthServer := http.Server{
		Addr:    fmt.Sprintf("0.0.0.0:%s", config.HealthPort),
		Handler: healthHandler,
	}
	go func() {
		// Run the health server in the "background"
		log.Println("Health server active on port", config.HealthPort)
		log.Fatalln(healthServer.ListenAndServe())
	}()
	log.Println("Git proxy active on port", config.ProxyPort)
	log.Println("Repo Url:", config.RepoUrl, "anonymous session:", config.AnonymousSession)
	log.Fatalln(proxyServer.ListenAndServe())
}

type gitProxyConfig struct {
	ProxyPort          string
	HealthPort         string
	AnonymousSession   bool
	EncodedCredentials string
	RepoUrl            *url.URL
}

// Parse the environment variables used as the configuration for the proxy.
func parseEnv() *gitProxyConfig {
	var ok, anonymousSession bool
	var gitlabOauthToken, proxyPort, healthPort, anonymousSessionStr, encodedCredentials string
	var repoUrl *url.URL
	if proxyPort, ok = os.LookupEnv("MITM_PROXY_PORT"); !ok {
		proxyPort = "8080"
	}
	if healthPort, ok = os.LookupEnv("HEALTH_PORT"); !ok {
		healthPort = "8081"
	}
	if anonymousSessionStr, ok = os.LookupEnv("ANONYMOUS_SESSION"); !ok {
		anonymousSessionStr = "true"
	}
	anonymousSession = anonymousSessionStr == "true"
	gitlabOauthToken = os.Getenv("GITLAB_OAUTH_TOKEN")
	encodedCredentials = encodeCredentials(gitlabOauthToken)
	repoUrl, err := url.Parse(os.Getenv("REPOSITORY_URL"))
	if err != nil {
		log.Fatal(err)
	}
	return &gitProxyConfig{
		ProxyPort:          proxyPort,
		HealthPort:         healthPort,
		AnonymousSession:   anonymousSession,
		EncodedCredentials: encodedCredentials,
		RepoUrl:            repoUrl,
	}
}

func encodeCredentials(token string) string {
	return base64.StdEncoding.EncodeToString([]byte(fmt.Sprintf("oauth2:%s", token)))
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
func getProxyHandler(config *gitProxyConfig) *goproxy.ProxyHttpServer {
	proxyHandler := goproxy.NewProxyHttpServer()
	proxyHandler.Verbose = true
	gitRepoHostWithWww := fmt.Sprintf("www.%s", config.RepoUrl.Hostname())
	handlerFunc := func(r *http.Request, ctx *goproxy.ProxyCtx) (*http.Request, *http.Response) {
		var validGitRequest bool
		validGitRequest = r.URL.Scheme == config.RepoUrl.Scheme &&
			hostsMatch(r.URL, config.RepoUrl) &&
			getPort(r.URL) == getPort(config.RepoUrl) &&
			strings.HasPrefix(strings.TrimLeft(r.URL.Path, "/"), strings.TrimLeft(config.RepoUrl.Path, "/"))
		if config.AnonymousSession {
			log.Print("Anonymous session, not adding auth headers, letting request through without adding auth headers.\n")
			return r, nil
		}
		if !validGitRequest {
			log.Println("The request", r.URL, "does not match the git repository", config.RepoUrl, ", letting request through without adding auth headers")
			return r, nil
		}
		log.Println("Adding auth header to request:", r.URL)
		r.Header.Set("Authorization", fmt.Sprintf("Basic %s", config.EncodedCredentials))
		return r, nil
	}
	// NOTE: We need to eavesdrop on the HTTPS connection to insert the Auth header
	// we do this only for the case where the request host matches the host of the git repo
	// in all other cases we leave the request alone.
	proxyHandler.OnRequest(goproxy.ReqHostIs(
		config.RepoUrl.Hostname(), 
		gitRepoHostWithWww,
		fmt.Sprintf("%s:443", config.RepoUrl.Hostname()), 
		fmt.Sprintf("%s:443", gitRepoHostWithWww), 
	)).HandleConnect(goproxy.AlwaysMitm)
	proxyHandler.OnRequest().DoFunc(handlerFunc)	
	return proxyHandler
}

// The proxy does not expose a health endpoint. Therefore the purpose of this server
// handler is to just fill that functionality. To ensure that the proxy is fully up
// and running the health server will use the proxy as a proxy for the health endpoint.
// This is necessary because sending any requests directly to the proxy results in a 500
// with a message that the proxy only accepts proxy requests and no direct requests.
func getHealthHandler(config *gitProxyConfig) *http.ServeMux {
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

	return handler
}
