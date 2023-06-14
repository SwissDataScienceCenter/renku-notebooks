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
	"strings"
	"sync"
	"time"

	"github.com/golang-jwt/jwt/v4"
)

type GitProxyConfig struct {
	// The port where the proxy is listening on
	ProxyPort string
	// The port (separate from the proxy) where the proxy will respond to status probes
	HealthPort string
	// True if this is an anonymous session
	AnonymousSession bool
	// The Git oauth token injected in Git requests by the proxy - not guaranteed to be a JWT.
	// Gitlab oauth tokens are not JWT tokens.
	gitAccessToken string
	// The unix epoch timestamp (in seconds) when the Git Oauth token expires
	gitAccessTokenExpiresAt int64
	// The oauth access token issued by Keycloak to a logged in Renku user
	renkuAccessToken string
	// The oauth refresh token issued by Keycloak to a logged in Renku user
	// It is assumed that the refresh tokens do not expire after use and can be reused.
	// This means that the 'Revoke Refresh Token' setting in the Renku realm in Keycloak
	// is not enabled.
	renkuRefreshToken string
	// The name of the Renku realm in Keycloak
	renkuRealm string
	// The Keycloak client ID to which the access token and refresh tokens were issued to
	renkuClientID string
	// The client secret for the client ID
	renkuClientSecret string
	// The URL of the project repository for the session
	RepoURL *url.URL
	// The url of the renku deployment
	RenkuURL *url.URL
	// How long should the proxy wait for a shutdown signal from the main session container
	// before it shuts down. This is needed because the git-proxy needs to wait for the session
	// to shutdown first. Because if the session wants to create an autosave branch but if the
	// proxy has already shut down then creating the autosave branch will fail and the unsaved
	// work from the session will be irrecoverably lost.
	SessionTerminationGracePeriod time.Duration
	// Used when the Git oauth token is refreshed. Ensures that the token is not refereshed
	// twice at the same time. It also ensures that all other threads that need to simply
	// read the token will wait until the refresh (write) is complete.
	gitAccessTokenLock   *sync.RWMutex
	renkuAccessTokenLock *sync.RWMutex
	// Safety margin for when to consider a token expired. For example if this is set to
	// 30 seconds then the token is considered expired if it expires in the next 30 seconds.
	expiredLeeway time.Duration
	// Channel that is populated by the timer that triggers the automated renku access token refresh
	refreshTicker *time.Ticker
}

// Parse the environment variables used as the configuration for the proxy.
func ParseEnv() *GitProxyConfig {
	var ok, anonymousSession bool
	var gitOauthToken, proxyPort, healthPort, anonymousSessionStr, SessionTerminationGracePeriodSeconds, renkuAccessToken, renkuClientID, renkuRealm, renkuClientSecret, renkuRefreshToken, renkuURL, gitOauthTokenExpiresAtRaw, refreshCheckPeriodSeconds, repoURL string
	var parsedRepoURL *url.URL
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
	if renkuAccessToken, ok = os.LookupEnv("RENKU_ACCESS_TOKEN"); !ok {
		log.Fatal("Cannot find required 'RENKU_ACCESS_TOKEN' environment variable\n")
	}
	if renkuRefreshToken, ok = os.LookupEnv("RENKU_REFRESH_TOKEN"); !ok {
		log.Fatal("Cannot find required 'RENKU_REFRESH_TOKEN' environment variable\n")
	}
	if renkuClientID, ok = os.LookupEnv("RENKU_CLIENT_ID"); !ok {
		log.Fatal("Cannot find required 'RENKU_CLIENT_ID' environment variable\n")
	}
	if renkuClientSecret, ok = os.LookupEnv("RENKU_CLIENT_SECRET"); !ok {
		log.Fatal("Cannot find required 'RENKU_CLIENT_SECRET' environment variable\n")
	}
	if renkuRealm, ok = os.LookupEnv("RENKU_REALM"); !ok {
		log.Fatal("Cannot find required 'RENKU_REALM' environment variable\n")
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
	if repoURL, ok = os.LookupEnv("REPOSITORY_URL"); !ok {
		log.Fatalln("Cannot find required 'REPOSITORY_URL' environment variable")
	}
	parsedRepoURL, err = url.Parse(repoURL)
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
	if refreshCheckPeriodSeconds, ok = os.LookupEnv("REFRESH_CHECK_PERIOD_SECONDS"); !ok {
		refreshCheckPeriodSeconds = "600"
	}
	refreshCheckPeriodSecondsParsed, err := strconv.ParseInt(refreshCheckPeriodSeconds, 10, 64)
	if err != nil {
		log.Fatalf("Cannot parse refresh period as integer %s: %s\n", refreshCheckPeriodSeconds, err.Error())
	}
	config := GitProxyConfig{
		ProxyPort:                     proxyPort,
		HealthPort:                    healthPort,
		AnonymousSession:              anonymousSession,
		gitAccessToken:                gitOauthToken,
		gitAccessTokenExpiresAt:       gitOauthTokenExpiresAt,
		renkuAccessToken:              renkuAccessToken,
		renkuRefreshToken:             renkuRefreshToken,
		renkuClientID:                 renkuClientID,
		renkuClientSecret:             renkuClientSecret,
		renkuRealm:                    renkuRealm,
		RepoURL:                       parsedRepoURL,
		RenkuURL:                      parsedRenkuURL,
		SessionTerminationGracePeriod: SessionTerminationGracePeriod,
		gitAccessTokenLock:            &sync.RWMutex{},
		renkuAccessTokenLock:          &sync.RWMutex{},
		expiredLeeway:                 time.Second * time.Duration(refreshCheckPeriodSecondsParsed) * 4,
		refreshTicker:                 time.NewTicker(time.Second * time.Duration(refreshCheckPeriodSecondsParsed)),
	}
	// Start a go routine to keep the refresh token valid
	go config.periodicTokenRefresh()
	return &config
}

func (c *GitProxyConfig) getRenkuAccessToken() string {
	c.renkuAccessTokenLock.RLock()
	defer c.renkuAccessTokenLock.RUnlock()
	return c.renkuAccessToken
}

// getRenkuAccessToken checks if the token is expired and if it is it will renew the token
// and return a new valid access token. If the token is valid it simply returns the access token.
func (c *GitProxyConfig) getAndRefreshRenkuAccessToken() (string, error) {
	isExpired, err := c.isJWTExpired(c.getRenkuAccessToken())
	if err != nil {
		return "", err
	}
	if isExpired {
		err = c.refreshRenkuAccessToken()
		if err != nil {
			return "", err
		}
	}
	return c.getRenkuAccessToken(), nil
}

// GetGitAccessToken will return a valid gitlab access token. If the token is expired
// it will call the gateway to get a new valid gitlab access token.
func (c *GitProxyConfig) GetGitAccessToken(encode bool) (string, error) {
	c.gitAccessTokenLock.RLock()
	accessTokenExpiresAt := c.gitAccessTokenExpiresAt
	c.gitAccessTokenLock.RUnlock()
	if accessTokenExpiresAt > 0 && time.Now().Unix() >= accessTokenExpiresAt-(c.expiredLeeway.Milliseconds()/1000) {
		log.Println("Refreshing git token")
		err := c.refreshGitAccessToken()
		if err != nil {
			return "", err
		}
	}
	c.gitAccessTokenLock.RLock()
	defer c.gitAccessTokenLock.RUnlock()
	if encode {
		return encodeGitCredentials(c.gitAccessToken), nil
	}
	return c.gitAccessToken, nil
}

func encodeGitCredentials(token string) string {
	return base64.StdEncoding.EncodeToString([]byte(fmt.Sprintf("oauth2:%s", token)))
}

type gitTokenRefreshResponse struct {
	AccessToken string `json:"access_token"`
	ExpiresAt   int64  `json:"expires_at"`
}

// Exchange the keycloak access token for a gitlab access token
func (c *GitProxyConfig) refreshGitAccessToken() (err error) {
	c.gitAccessTokenLock.Lock()
	defer c.gitAccessTokenLock.Unlock()
	req, err := http.NewRequest(http.MethodGet, c.RenkuURL.JoinPath("api/auth/gitlab/exchange").String(), nil)
	if err != nil {
		return
	}
	renkuAccessToken, err := c.getAndRefreshRenkuAccessToken()
	if err != nil {
		return
	}
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", renkuAccessToken))
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return
	}
	if res.StatusCode != 200 {
		err = fmt.Errorf("cannot exchange keycloak oauth token for git token, failed with staus code: %d", res.StatusCode)
		return
	}
	var resParsed gitTokenRefreshResponse
	err = json.NewDecoder(res.Body).Decode(&resParsed)
	if err != nil {
		return
	}
	c.gitAccessToken = resParsed.AccessToken
	c.gitAccessTokenExpiresAt = resParsed.ExpiresAt
	return nil
}

type renkuTokenRefreshResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
}

// refreshRenkuAccessToken calls keycloak with a refresh token to get a new access token
func (c *GitProxyConfig) refreshRenkuAccessToken() (err error) {
	c.renkuAccessTokenLock.Lock()
	defer c.renkuAccessTokenLock.Unlock()
	payload := url.Values{}
	payload.Add("grant_type", "refresh_token")
	payload.Add("refresh_token", c.renkuRefreshToken)
	body := strings.NewReader(payload.Encode())
	req, err := http.NewRequest(http.MethodPost, c.RenkuURL.JoinPath(fmt.Sprintf("auth/realms/%s/protocol/openid-connect/token", c.renkuRealm)).String(), body)
	if err != nil {
		return
	}
	req.SetBasicAuth(c.renkuClientID, c.renkuClientSecret)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return
	}
	if res.StatusCode != 200 {
		err = fmt.Errorf("cannot refresh keycloak token, failed with staus code: %d", res.StatusCode)
		return
	}
	var resParsed renkuTokenRefreshResponse
	err = json.NewDecoder(res.Body).Decode(&resParsed)
	if err != nil {
		return
	}
	c.renkuAccessToken = resParsed.AccessToken
	if resParsed.RefreshToken != "" {
		c.renkuRefreshToken = resParsed.RefreshToken
	}
	return nil
}

// Checks if the expiry of the token has passed or is coming up soon based on a predefined threshold.
// NOTE: no signature validation is performed at all. All of the tokens in the proxy are trusted implicitly
// because they comes from trusted/controlled sources.
func (c *GitProxyConfig) isJWTExpired(token string) (isExpired bool, err error) {
	parser := jwt.NewParser()
	claims := jwt.RegisteredClaims{}
	isExpired = true
	_, _, err = parser.ParseUnverified(token, &claims)
	if err != nil {
		log.Printf("Cannot parse token claims, assuming token is expired: %s\n", err.Error())
		return
	}
	// VerifyExpiresAt returns cmp.Before(exp) if exp is set, otherwise !req if exp is not set.
	// Here we have it setup so that if the exp claim is not defined we assume the token is not expired.
	// Keycloak does not set the `exp` claim on tokens that have the offline access grant - because they do not expire.
	jwtIsNotExpired := claims.VerifyExpiresAt(time.Now().Add(c.expiredLeeway), false)
	return !jwtIsNotExpired, nil
}

// Periodically refreshes the renku acces token. Used to make sure the refresh token does not expire.
func (c *GitProxyConfig) periodicTokenRefresh() {
	for {
		<-c.refreshTicker.C
		c.renkuAccessTokenLock.RLock()
		renkuRefreshToken := c.renkuRefreshToken
		c.renkuAccessTokenLock.RUnlock()
		refreshTokenIsExpired, err := c.isJWTExpired(renkuRefreshToken)
		if err != nil {
			log.Printf("Could not check if renku refresh token is expired: %s\n", err.Error())
		}
		if refreshTokenIsExpired {
			log.Println("Getting a new renku refresh token from automatic checks")
			err = c.refreshRenkuAccessToken()
			if err != nil {
				log.Printf("Could not refresh renku token: %s\n", err.Error())
			}
		}
	}
}
