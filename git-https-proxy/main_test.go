package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

const gitAuthToken string = "verySecretToken"

// This is a dummy server meant to mimic the final
// destionation the proxy will route a request to. The
// server just returns information about the received request
// and nothing else. Used to confirm that the proxy is properly
// routing things and injecting the right headers.
func setUpGitServer() (*url.URL, func()) {
	handler := http.NewServeMux()
	handlerFunc := func(w http.ResponseWriter, r *http.Request) {
		var body []byte
		var err error
		body, err = io.ReadAll(r.Body)
		if err != nil {
			log.Fatalln("Cannot read body from response")
		}
		for name, values := range r.Header {
			w.Header().Set(name, values[0])
		}
		w.Write(body)
		w.WriteHeader(http.StatusOK)
	}
	handler.HandleFunc("/", handlerFunc)
	return setUpTestServer(handler)
}

func setUpGitProxy(config *gitProxyConfig) (*url.URL, func()) {
	proxyHandler := getProxyHandler(config)
	return setUpTestServer(proxyHandler)
}

func setUpTestServer(handler http.Handler) (*url.URL, func()) {
	ts := httptest.NewServer(handler)
	tsUrl, err := url.Parse(ts.URL)
	if err != nil {
		log.Fatalln(err)
	}
	return tsUrl, ts.Close
}

func getTestConfig(isSessionAnonymous bool, token string, injectionUrl *url.URL) *gitProxyConfig {
	return &gitProxyConfig{
		ProxyPort:          "",
		HealthPort:         "",
		AnonymousSession:   isSessionAnonymous,
		EncodedCredentials: encodeCredentials(token),
		RepoUrl:            injectionUrl,
		SessionTerminationGracePeriod: 30 * time.Second,
	}
}

func getTestClient(proxyUrl *url.URL) *http.Client {
	return &http.Client{Transport: &http.Transport{Proxy: http.ProxyURL(proxyUrl)}}
}

type testEntry struct {
    Url string
    AuthHeader string
}

// Ensure token is not sent when user is anonymous
func TestProxyAnonymous(t *testing.T) {
    gitServerUrl, gitServerClose := setUpGitServer()
	defer gitServerClose()
	injectionPath := &url.URL{
		Scheme: gitServerUrl.Scheme,
		Host:   gitServerUrl.Host,
		Path:   "injection/path",
	}
	config := getTestConfig(true, gitAuthToken, injectionPath)
	proxyServerUrl, proxyServerClose := setUpGitProxy(config)
	defer proxyServerClose()
	testClient := getTestClient(proxyServerUrl)
    tests := []testEntry{
        {Url: gitServerUrl.String(), AuthHeader: ""},
        {Url: injectionPath.String(), AuthHeader: ""},
    }
    for _, test := range tests {
        resp, err := testClient.Get(test.Url)
        assert.Nil(t, err)
        assert.Equal(t, resp.Header.Get("Authorization"), test.AuthHeader)
    }
}

//Ensure token is sent in header only when urls match
func TestProxyRegistered(t *testing.T) {
	gitServerUrl, gitServerClose := setUpGitServer()
	defer gitServerClose()
	injectionPath := &url.URL{
		Scheme: gitServerUrl.Scheme,
		Host:   gitServerUrl.Host,
		Path:   "injection/path",
	}
	config := getTestConfig(false, gitAuthToken, injectionPath)
	proxyServerUrl, proxyServerClose := setUpGitProxy(config)
	defer proxyServerClose()
	testClient := getTestClient(proxyServerUrl)
    authHeaderValue := fmt.Sprintf("Basic %s", encodeCredentials(gitAuthToken))
    tests := []testEntry{
	    // Path is root and does not match repo url
        {Url: gitServerUrl.String(), AuthHeader: ""},
	    // Path is not root and does not match repo url
        {Url: fmt.Sprintf("%s/%s", gitServerUrl.String(), "some/subpath"), AuthHeader: ""},
	    // Path exactly matches repo url
        {Url: injectionPath.String(), AuthHeader: authHeaderValue},
	    // Path begins with repo url
        {Url: fmt.Sprintf("%s/%s", injectionPath.String(), "some/subpath"), AuthHeader: authHeaderValue},
    }
    for _, test := range tests {
        resp, err := testClient.Get(test.Url)
        assert.Nil(t, err)
        assert.Equal(t, resp.Header.Get("Authorization"), test.AuthHeader)
    }
}
