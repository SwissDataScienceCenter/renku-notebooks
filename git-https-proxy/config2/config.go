package config2

import (
	"encoding/json"
	"fmt"
	"reflect"

	"github.com/mitchellh/mapstructure"
	"github.com/spf13/viper"
)

type GitRepository struct {
	Url      string `json:"url"`
	Provider string `json:"provider"`
}

type GitProvider struct {
	Id             string `json:"id"`
	AccessTokenUrl string `json:"access_token_url"`
}

type GitProxyConfig struct {
	// The port where the proxy is listening on
	ProxyPort int `mapstructure:"port"`
	// The port (separate from the proxy) where the proxy will respond to status probes
	HealthPort int `mapstructure:"health_port"`
	// True if this is an anonymous session
	AnonymousSession bool `mapstructure:"anonymous_session"`

	// The git repositories to proxy
	Repositories []GitRepository `mapstructure:"repositories"`
	// The git providers
	Providers []GitProvider `mapstructure:"providers"`
}

func GetConfig() (GitProxyConfig, error) {
	v := viper.New()
	v.SetConfigType("env")
	v.SetEnvPrefix("git_proxy")
	v.AutomaticEnv()

	v.SetDefault("port", 8080)
	v.SetDefault("health_port", 8081)
	v.SetDefault("anonymous_session", true)
	v.SetDefault("repositories", []GitRepository{})
	v.SetDefault("providers", []GitProvider{})

	var config GitProxyConfig
	dh := viper.DecodeHook(mapstructure.ComposeDecodeHookFunc(parseJsonArray(), parseJsonVariable()))
	if err := v.Unmarshal(&config, dh); err != nil {
		return GitProxyConfig{}, err
	}

	return config, nil
}

func parseJsonArray() mapstructure.DecodeHookFuncType {
	return func(f reflect.Type, t reflect.Type, data any) (interface{}, error) {
		// Check that the data is a string
		if f.Kind() != reflect.String {
			return data, nil
		}

		// Check that the target type is a slice
		if t.Kind() != reflect.Slice {
			return data, nil
		}

		raw := data.(string)
		if raw == "" {
			return nil, fmt.Errorf("cannot parse empty string as a slice")
		}

		var slice []json.RawMessage
		if err := json.Unmarshal([]byte(raw), &slice); err != nil {
			return data, nil
		}

		var value []string
		for _, v := range slice {
			value = append(value, string(v))
		}

		return value, nil
	}
}

func parseJsonVariable() mapstructure.DecodeHookFuncType {
	return func(f reflect.Type, t reflect.Type, data any) (interface{}, error) {
		// Check that the data is a string
		if f.Kind() != reflect.String {
			return data, nil
		}

		// Check that the target type is a struct
		if t.Kind() != reflect.Struct {
			return data, nil
		}

		raw := data.(string)
		if raw == "" {
			return nil, fmt.Errorf("cannot parse empty string as a struct")
		}

		value := reflect.New(t)
		if err := json.Unmarshal([]byte(raw), value.Interface()); err != nil {
			return data, nil
		}

		return value.Interface(), nil
	}
}
