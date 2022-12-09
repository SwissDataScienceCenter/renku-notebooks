package config

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v4"
	"github.com/stretchr/testify/assert"
)

func getTestConfig(renkuUrl string, gitAccessToken string, gitAccessTokenExpiresAt int64, renkuAccessToken string, renkuRefreshToken string, refreshPeriodSeconds string) *GitProxyConfig {
	os.Setenv("GITLAB_OAUTH_TOKEN", gitAccessToken)
	defer os.Unsetenv("GITLAB_OAUTH_TOKEN")
	os.Setenv("GITLAB_OAUTH_TOKEN_EXPIRES_AT", fmt.Sprintf("%d", gitAccessTokenExpiresAt))
	defer os.Unsetenv("GITLAB_OAUTH_TOKEN_EXPIRES_AT")
	os.Setenv("RENKU_ACCESS_TOKEN", renkuAccessToken)
	defer os.Unsetenv("RENKU_ACCESS_TOKEN")
	os.Setenv("RENKU_URL", renkuUrl)
	defer os.Unsetenv("RENKU_URL")
	os.Setenv("REPOSITORY_URL", "https://dummy.renku.com")
	defer os.Unsetenv("REPOSITORY_URL")
	os.Setenv("ANONYMOUS_SESSION", "false")
	defer os.Unsetenv("ANONYMOUS_SESSION")
	os.Setenv("RENKU_REALM", "Renku")
	defer os.Unsetenv("RENKU_REALM")
	os.Setenv("RENKU_REFRESH_TOKEN", renkuRefreshToken)
	defer os.Unsetenv("RENKU_REFRESH_TOKEN")
	os.Setenv("RENKU_CLIENT_ID", "RenkuClientID")
	defer os.Unsetenv("RENKU_CLIENT_ID")
	os.Setenv("RENKU_CLIENT_SECRET", "RenkuClientSecret")
	defer os.Unsetenv("RENKU_CLIENT_SECRET")
	os.Setenv("REFRESH_CHECK_PERIOD_SECONDS", refreshPeriodSeconds)
	defer os.Unsetenv("REFRESH_CHECK_PERIOD_SECONDS")
	return ParseEnv()
}

func setUpTestServer(handler http.Handler) (*url.URL, func()) {
	ts := httptest.NewServer(handler)
	tsURL, err := url.Parse(ts.URL)
	if err != nil {
		log.Fatalln(err)
	}
	return tsURL, ts.Close
}

func setUpDummyRefreshEndpoints(gitRefreshResponse *gitTokenRefreshResponse, renkuRefreshResponse *renkuTokenRefreshResponse) (*url.URL, func()) {
	handler := http.NewServeMux()
	gitHandlerFunc := func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Handling git token refresh request at %s", r.URL.String())
		if gitRefreshResponse == nil {
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte("Cannot refresh git token"))
		}
		json.NewEncoder(w).Encode(gitRefreshResponse)
	}
	renkuHandlerFunc := func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Handling renku token refresh request at %s", r.URL.String())
		if renkuRefreshResponse == nil {
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte("Cannot refresh renku token"))
		}
		json.NewEncoder(w).Encode(renkuRefreshResponse)
	}
	handler.HandleFunc("/api/auth/gitlab/exchange", gitHandlerFunc)
	handler.HandleFunc("/auth/realms/Renku/protocol/openid-connect/token", renkuHandlerFunc)
	return setUpTestServer(handler)
}

type DummySigningMethod struct{}

func (d DummySigningMethod) Verify(signingString, signature string, key interface{}) error {
	return nil
}

func (d DummySigningMethod) Sign(signingString string, key interface{}) (string, error) {
	return base64.URLEncoding.EncodeToString([]byte(signingString)), nil
}

func (d DummySigningMethod) Alg() string { return "none" }

func getDummyAccessToken(expiresAt int64) (token string, err error) {
	t := jwt.New(DummySigningMethod{})
	t.Claims = &jwt.StandardClaims{
		ExpiresAt: expiresAt,
	}
	return t.SignedString(nil)
}

func TestSuccessfulRefresh(t *testing.T) {
	newGitToken := "newGitToken"
	oldGitToken := "oldGitToken"
	newRenkuToken, err := getDummyAccessToken(time.Now().Unix() + 3600)
	assert.Nil(t, err)
	oldRenkuAccessToken, err := getDummyAccessToken(time.Now().Unix() - 3600)
	assert.Nil(t, err)
	oldRenkuRefreshToken, err := getDummyAccessToken(time.Now().Unix() + 7200)
	assert.Nil(t, err)
	gitRefreshResponse := &gitTokenRefreshResponse{
		AccessToken: newGitToken,
		ExpiresAt:   time.Now().Unix() + 3600,
	}
	renkuRefreshResponse := &renkuTokenRefreshResponse{
		AccessToken: newRenkuToken,
		RefreshToken: oldRenkuRefreshToken,
	}
	authServerURL, authServerClose := setUpDummyRefreshEndpoints(gitRefreshResponse, renkuRefreshResponse)
	log.Printf("Dummy refresh server running at %s\n", authServerURL.String())
	defer authServerClose()

	// token refresh is needed and succeeds
	config := getTestConfig(authServerURL.String(), oldGitToken, time.Now().Unix()-9999999, oldRenkuAccessToken, oldRenkuRefreshToken, "600")
	gitToken, err := config.GetGitAccessToken(false)
	assert.Nil(t, err)
	assert.Equal(t, gitToken, newGitToken)
	renkuAccessToken, err := config.getAndRefreshRenkuAccessToken()
	assert.Nil(t, err)
	assert.Equal(t, renkuAccessToken, newRenkuToken)

	// change token in server response
	// assert that immediately after the refresh the token is valid and is not refreshed again
	gitRefreshResponse.AccessToken = "SomethingElse"
	evenNewerRenkuToken, err := getDummyAccessToken(time.Now().Unix() + 7200)
	assert.Nil(t, err)
	renkuRefreshResponse.AccessToken = evenNewerRenkuToken
	gitToken, err = config.GetGitAccessToken(false)
	assert.Nil(t, err)
	assert.Equal(t, gitToken, newGitToken)
	renkuAccessToken, err = config.getAndRefreshRenkuAccessToken()
	assert.Nil(t, err)
	assert.Equal(t, renkuAccessToken, newRenkuToken)
}

func TestNoRefreshNeeded(t *testing.T) {
	oldGitToken := "oldGitToken"
	oldRenkuAccessToken, err := getDummyAccessToken(time.Now().Unix() + 3600)
	assert.Nil(t, err)
	oldRenkuRefreshToken, err := getDummyAccessToken(time.Now().Unix() + 7200)
	assert.Nil(t, err)
	// Passing nil means that if the any tokens are attempted to be refreshed errors will be returned
	authServerURL, authServerClose := setUpDummyRefreshEndpoints(nil, nil)
	defer authServerClose()

	config := getTestConfig(authServerURL.String(), oldGitToken, time.Now().Unix()+99999, oldRenkuAccessToken, oldRenkuRefreshToken, "600")
	gitToken, err := config.GetGitAccessToken(false)
	assert.Nil(t, err)
	assert.Equal(t, gitToken, oldGitToken)
	renkuAccessToken, err := config.getAndRefreshRenkuAccessToken()
	assert.Nil(t, err)
	assert.Equal(t, renkuAccessToken, oldRenkuAccessToken)
}

func TestAutomatedRefreshTokenRenewal(t *testing.T) {
	newRenkuAccessToken, err := getDummyAccessToken(time.Now().Unix() + 3600)
	assert.Nil(t, err)
	newRenkuRefreshToken, err := getDummyAccessToken(time.Now().Unix() + (3600 * 24))
	assert.Nil(t, err)
	oldRenkuAccessToken, err := getDummyAccessToken(time.Now().Unix() - 3600)
	assert.Nil(t, err)
	oldRenkuRefreshToken, err := getDummyAccessToken(time.Now().Unix() + 10)
	assert.Nil(t, err)
	renkuRefreshResponse := &renkuTokenRefreshResponse{
		AccessToken: newRenkuAccessToken,
		RefreshToken: newRenkuRefreshToken,
	}
	authServerURL, authServerClose := setUpDummyRefreshEndpoints(nil, renkuRefreshResponse)
	log.Printf("Dummy refresh server running at %s\n", authServerURL.String())
	defer authServerClose()

	config := getTestConfig(authServerURL.String(), "", time.Now().Unix()+3600, oldRenkuAccessToken, oldRenkuRefreshToken, "2")
	assert.Equal(t, config.getRenkuAccessToken(), oldRenkuAccessToken)
	assert.Equal(t, config.renkuRefreshToken, oldRenkuRefreshToken)
	// Sleep to allow for automated token refresh to occur
	time.Sleep(time.Second * 5)
	assert.Equal(t, config.getRenkuAccessToken(), newRenkuAccessToken)
	assert.Equal(t, config.renkuRefreshToken, newRenkuRefreshToken)
}
