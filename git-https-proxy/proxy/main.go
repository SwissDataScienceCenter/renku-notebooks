package proxy

import (
	"fmt"
	"log"
	"net/url"
	"regexp"

	"github.com/SwissDataScienceCenter/renku-notebooks/git-https-proxy/config2"
	"github.com/elazarl/goproxy"
)

// Return a server handler that contains the proxy that injects the Git aithorization header when
// the conditions for doing so are met.
func GetProxyHandler(config config2.GitProxyConfig) *goproxy.ProxyHttpServer {
	proxyHandler := goproxy.NewProxyHttpServer()
	proxyHandler.Verbose = false
	// gitRepoHostWithWww := fmt.Sprintf("www.%s", config.RepoURL.Hostname())

	// handlerFunc := func(r *http.Request, ctx *goproxy.ProxyCtx) (*http.Request, *http.Response) {
	// 	var validGitRequest bool
	// 	validGitRequest = r.URL.Scheme == config.RepoURL.Scheme &&
	// 		hostsMatch(r.URL, config.RepoURL) &&
	// 		getPort(r.URL) == getPort(config.RepoURL) &&
	// 		strings.HasPrefix(strings.TrimLeft(r.URL.Path, "/"), strings.TrimLeft(config.RepoURL.Path, "/"))
	// 	if config.AnonymousSession {
	// 		log.Print("Anonymous session, not adding auth headers, letting request through without adding auth headers.\n")
	// 		return r, nil
	// 	}
	// 	if !validGitRequest {
	// 		// Skip logging healthcheck requests
	// 		if r.URL.Path != "/ping" && r.URL.Path != "/ping/" {
	// 			log.Printf("The request %s does not match the git repository %s letting request through without adding auth headers\n", r.URL.String(), config.RepoURL.String())
	// 		}
	// 		return r, nil
	// 	}
	// 	log.Printf("The request %s matches the git repository %s, adding auth headers\n", r.URL.String(), config.RepoURL.String())
	// 	gitToken, err := config.GetGitAccessToken(true)
	// 	if err != nil {
	// 		log.Printf("The git token cannot be refreshed, returning 401, error: %s\n", err.Error())
	// 		return r, goproxy.NewResponse(r, goproxy.ContentTypeText, 401, "The git token could not be refreshed")
	// 	}
	// 	r.Header.Set("Authorization", fmt.Sprintf("Basic %s", gitToken))
	// 	return r, nil
	// }

	// NOTE: We need to eavesdrop on the HTTPS connection to insert the Auth header
	// we do this only for the case where the request host matches the host of the git repo
	// in all other cases we leave the request alone.
	// proxyHandler.OnRequest(goproxy.ReqHostIs(
	// 	config.RepoURL.Hostname(),
	// 	gitRepoHostWithWww,
	// 	fmt.Sprintf("%s:443", config.RepoURL.Hostname()),
	// 	fmt.Sprintf("%s:443", gitRepoHostWithWww),
	// )).HandleConnect(goproxy.AlwaysMitm)
	// proxyHandler.OnRequest().DoFunc(handlerFunc)
	return proxyHandler
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
