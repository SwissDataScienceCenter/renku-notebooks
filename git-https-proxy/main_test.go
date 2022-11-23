package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"
	"time"

	configLib "github.com/SwissDataScienceCenter/renku-notebooks/git-https-proxy/config"
	"github.com/stretchr/testify/assert"
)

const gitAuthToken string = "verySecretToken"
const renkuJWT string = "verySecretRenkuJWT"

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
		w.WriteHeader(http.StatusOK)
		w.Write(body)
	}
	handler.HandleFunc("/", handlerFunc)
	return setUpTestServer(handler)
}

func setUpGitProxy(c configLib.GitProxyConfig) (*url.URL, func()) {
	proxyHandler := getProxyHandler(c)
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

func getTestConfig(isSessionAnonymous bool, token string, injectionURL *url.URL) configLib.GitProxyConfig {
	os.Setenv("GITLAB_OAUTH_TOKEN", token)
	defer os.Unsetenv("GITLAB_OAUTH_TOKEN")
	os.Setenv("GITLAB_OAUTH_TOKEN_EXPIRES_AT", fmt.Sprintf("%d", time.Now().Unix()+9999999999))
	defer os.Unsetenv("GITLAB_OAUTH_TOKEN_EXPIRES_AT")
	os.Setenv("RENKU_JWT", renkuJWT)
	defer os.Unsetenv("RENKU_JWT")
	os.Setenv("RENKU_URL", "https://dummy.renku.com")
	defer os.Unsetenv("RENKU_URL")
	os.Setenv("REPOSITORY_URL", injectionURL.String())
	defer os.Unsetenv("REPOSITORY_URL")
	os.Setenv("ANONYMOUS_SESSION", fmt.Sprint(isSessionAnonymous))
	defer os.Unsetenv("ANONYMOUS_SESSION")
	return configLib.ParseEnv()
}

func getTestClient(proxyUrl *url.URL) *http.Client {
	return &http.Client{Transport: &http.Transport{Proxy: http.ProxyURL(proxyUrl)}}
}

type testEntry struct {
	Url        string
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

// Ensure token is sent in header only when urls match
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
	token, err := config.GetGitOauthToken(true)
	assert.Nil(t, err)
	authHeaderValue := fmt.Sprintf("Basic %s", token)
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
