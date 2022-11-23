package config

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func getTestConfig(renkuUrl string, gitToken string, gitTokenExpiresAt int64, renkuToken string) GitProxyConfig {
	os.Setenv("GITLAB_OAUTH_TOKEN", gitToken)
	defer os.Unsetenv("GITLAB_OAUTH_TOKEN")
	os.Setenv("GITLAB_OAUTH_TOKEN_EXPIRES_AT", fmt.Sprintf("%d", gitTokenExpiresAt))
	defer os.Unsetenv("GITLAB_OAUTH_TOKEN_EXPIRES_AT")
	os.Setenv("RENKU_JWT", renkuToken)
	defer os.Unsetenv("RENKU_JWT")
	os.Setenv("RENKU_URL", renkuUrl)
	defer os.Unsetenv("RENKU_URL")
	os.Setenv("REPOSITORY_URL", "https://dummy.renku.com")
	defer os.Unsetenv("REPOSITORY_URL")
	os.Setenv("ANONYMOUS_SESSION", "false")
	defer os.Unsetenv("ANONYMOUS_SESSION")
	return ParseEnv()
}

func setUpTestServer(handler http.Handler) (*url.URL, func()) {
	ts := httptest.NewServer(handler)
	tsUrl, err := url.Parse(ts.URL)
	if err != nil {
		log.Fatalln(err)
	}
	return tsUrl, ts.Close
}

func setUpAuthServer(refreshResponse *tokenRefreshResponse) (*url.URL, func()) {
	handler := http.NewServeMux()
	handlerFunc := func(w http.ResponseWriter, r *http.Request) {
		log.Println("Handling refresh token request")
		if refreshResponse == nil {
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte("Cannot refresh token"))
		}
		json.NewEncoder(w).Encode(refreshResponse)
	}
	handler.HandleFunc("/", handlerFunc)
	return setUpTestServer(handler)
}

func TestSuccessfulRefresh(t *testing.T) {
	newGitToken := "newGitToken"
	newRenkuToken := "newRenkuToken"
	refreshResponse := &tokenRefreshResponse{
		Git: struct {
			AccessToken string `json:"access_token"`
			ExpiresAt   int64  `json:"expires_at"`
		}{
			AccessToken: newGitToken,
			ExpiresAt:   time.Now().Unix() + 999999999999,
		},
		Renku: struct {
			AccessToken string `json:"access_token"`
		}{
			AccessToken: newRenkuToken,
		},
	}
	authServerURL, authServerClose := setUpAuthServer(refreshResponse)
	defer authServerClose()

	// token refresh is needed and succeeds
	config := getTestConfig(authServerURL.String(), "oldGitToken", time.Now().Unix()-9999999, "oldRenkuToken")
	gitToken, err := config.GetGitOauthToken(false)
	assert.Nil(t, err)
	assert.Equal(t, gitToken, newGitToken)
	assert.Equal(t, config.GetRenkuJWT(), newRenkuToken)

	// change token in server response
	// assert that immediately after the refresh the token is valid and is not refreshed again
	refreshResponse.Git.AccessToken = "SomethingElse"
	refreshResponse.Renku.AccessToken = "SomethingElse"
	gitToken, err = config.GetGitOauthToken(false)
	assert.Nil(t, err)
	assert.Equal(t, gitToken, newGitToken)
	assert.Equal(t, config.GetRenkuJWT(), newRenkuToken)
}

func TestNoRefreshNeeded(t *testing.T) {
	oldGitToken := "oldGitToken"
	oldRenkuToken := "oldRenkuToken"
	authServerURL, authServerClose := setUpAuthServer(nil)
	defer authServerClose()

	config := getTestConfig(authServerURL.String(), oldGitToken, time.Now().Unix()+99999, oldRenkuToken)
	gitToken, err := config.GetGitOauthToken(false)
	assert.Nil(t, err)
	assert.Equal(t, gitToken, oldGitToken)
	assert.Equal(t, config.GetRenkuJWT(), oldRenkuToken)
}
