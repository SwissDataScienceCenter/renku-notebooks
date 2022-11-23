// Package config stores the configuration for a git proxy.
// It also manages and refreshes the renku and git oauth tokens it stores.
package config

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"sync"
	"time"
)

type GitProxyConfig struct {
	// The port where the proxy is listening on
	ProxyPort string
	// The port (separate from the proxy) where the proxy will respond to status probes
	HealthPort string
	// True if this is an anonymous seession
	AnonymousSession bool
	// The Git oauth token injected in Git requests by the proxy - not guaranteed to be a JWT.
	// Gitlab oauth tokens are not JWT tokens.
	gitOauthToken string
	// The unix epoch timestamp (in seconds) when the Git Oauth token expires
	gitOauthTokenExpiresAt int64
	// The JWT oauth token issued by Keycloak to a logged in Renku user
	renkuJWT string
	// The URL of the project repository for the session
	RepoURL *url.URL
	// The url of the renku deployment
	RenkuURL *url.URL
	// How long should the proxy wait for a shutdown signal from the main session container
	// before it shuts down. This is needed because the git-proxy needs to wait for the session
	// to shutdown first. Because if the session wants to create an autosave branch but if the
	// proxy has already shut down then creating the autosave branch will fail and the unsaved
	// work from the session will be irrecoverably lost,
	SessionTerminationGracePeriod time.Duration
	// Used when the Git oauth token is refreshed. Ensures that the token is not refereshed
	// twice at the same time. It also ensures that all other threads that need to simply
	// read the token will wait until the refresh (write) is complete.
	gitTokenLock *sync.RWMutex
	renkuJWTLock *sync.RWMutex
}

// Parse the environment variables used as the configuration for the proxy.
func ParseEnv() GitProxyConfig {
	var ok, anonymousSession bool
	var gitOauthToken, proxyPort, healthPort, anonymousSessionStr, SessionTerminationGracePeriodSeconds, renkuJWT, renkuURL, gitOauthTokenExpiresAtRaw string
	var repoURL *url.URL
	var err error
	var gitOauthTokenExpiresAt int64
	var SessionTerminationGracePeriod time.Duration
	if proxyPort, ok = os.LookupEnv("GIT_PROXY_PORT"); !ok {
		proxyPort = "8080"
	}
	if healthPort, ok = os.LookupEnv("GIT_PROXY_HEALTH_PORT"); !ok {
		healthPort = "8081"
	}
	if anonymousSessionStr, ok = os.LookupEnv("ANONYMOUS_SESSION"); !ok {
		anonymousSessionStr = "true"
	}
	anonymousSession = anonymousSessionStr == "true"
	if SessionTerminationGracePeriodSeconds, ok = os.LookupEnv("SESSION_TERMINATION_GRACE_PERIOD_SECONDS"); !ok {
		SessionTerminationGracePeriodSeconds = "600"
	}
	SessionTerminationGracePeriodSeconds = fmt.Sprintf("%ss", SessionTerminationGracePeriodSeconds)
	SessionTerminationGracePeriod, err = time.ParseDuration(SessionTerminationGracePeriodSeconds)
	if err != nil {
		log.Fatalf("Cannot parse 'SESSION_TERMINATION_GRACE_PERIOD_SECONDS' %s: %s\n", SessionTerminationGracePeriodSeconds, err.Error())
	}
	if renkuJWT, ok = os.LookupEnv("RENKU_JWT"); !ok {
		log.Fatal("Cannot find required 'RENKU_JWT' environment variable\n")
	}
	if gitOauthToken, ok = os.LookupEnv("GITLAB_OAUTH_TOKEN"); !ok {
		log.Fatal("Cannot find required 'GITLAB_OAUTH_TOKEN' environment variable\n")
	}
	if gitOauthTokenExpiresAtRaw, ok = os.LookupEnv("GITLAB_OAUTH_TOKEN_EXPIRES_AT"); !ok {
		log.Fatal("Cannot find required 'GITLAB_OAUTH_TOKEN_EXPIRES_AT' environment variable\n")
	}
	if gitOauthTokenExpiresAt, err = strconv.ParseInt(gitOauthTokenExpiresAtRaw, 10, 64); err != nil {
		log.Fatalf("Cannot convert 'GITLAB_OAUTH_TOKEN_EXPIRES_AT' environment variable %s to integer\n", gitOauthTokenExpiresAtRaw)
	}
	repoURL, err = url.Parse(os.Getenv("REPOSITORY_URL"))
	if err != nil {
		log.Fatalf("Cannot parse 'REPOSITORY_URL': %s", err.Error())
	}
	if renkuURL, ok = os.LookupEnv("RENKU_URL"); !ok {
		log.Fatal("Cannot find required 'RENKU_URL' environment variable\n")
	}
	parsedRenkuURL, err := url.Parse(renkuURL)
	if err != nil {
		log.Fatalf("Cannot parse 'RENKU_URL' %s: %s", renkuURL, err.Error())
	}
	return GitProxyConfig{
		ProxyPort:                     proxyPort,
		HealthPort:                    healthPort,
		AnonymousSession:              anonymousSession,
		gitOauthToken:                 gitOauthToken,
		gitOauthTokenExpiresAt:        gitOauthTokenExpiresAt,
		renkuJWT:                      renkuJWT,
		RepoURL:                       repoURL,
		RenkuURL:                      parsedRenkuURL,
		SessionTerminationGracePeriod: SessionTerminationGracePeriod,
		gitTokenLock:                  &sync.RWMutex{},
		renkuJWTLock:                  &sync.RWMutex{},
	}
}

func (c *GitProxyConfig) GetRenkuJWT() string {
	c.renkuJWTLock.RLock()
	defer c.renkuJWTLock.RUnlock()
	return c.renkuJWT
}

func (c *GitProxyConfig) GetGitOauthToken(encode bool) (string, error) {
	if time.Now().Unix() >= c.gitOauthTokenExpiresAt+30 {
		log.Println("Refreshing git token")
		err := c.refreshOauthTokens()
		if err != nil {
			return "", err
		}
	}
	c.gitTokenLock.RLock()
	defer c.gitTokenLock.RUnlock()
	if encode {
		return encodeGitCredentials(c.gitOauthToken), nil
	}
	return c.gitOauthToken, nil
}

func encodeGitCredentials(token string) string {
	return base64.StdEncoding.EncodeToString([]byte(fmt.Sprintf("oauth2:%s", token)))
}

type tokenRefreshResponse struct {
	Git struct {
		AccessToken string `json:"access_token"`
		ExpiresAt   int64  `json:"expires_at"`
	}
	Renku struct {
		AccessToken string `json:"access_token"`
	}
}

// Exchange the keycloak oauth token for a gitlab token
// The gateway will also refresh the keycloak token and return a new
// one if it is expired.
func (c *GitProxyConfig) refreshOauthTokens() (err error) {
	c.gitTokenLock.Lock()
	c.renkuJWTLock.Lock()
	defer c.gitTokenLock.Unlock()
	defer c.renkuJWTLock.Unlock()
	req, err := http.NewRequest(http.MethodPost, c.RenkuURL.JoinPath("api/auth/gitlab/exchange").String(), nil)
	if err != nil {
		return
	}
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.renkuJWT))
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return
	}
	if res.StatusCode != 200 {
		err = fmt.Errorf("cannot exchange keycloak oauth token for git token, failed with staus code: %d", res.StatusCode)
		return
	}
	var resParsed tokenRefreshResponse
	err = json.NewDecoder(res.Body).Decode(&resParsed)
	if err != nil {
		return
	}
	c.gitOauthToken = resParsed.Git.AccessToken
	c.renkuJWT = resParsed.Renku.AccessToken
	c.gitOauthTokenExpiresAt = resParsed.Git.ExpiresAt
	return nil
}
