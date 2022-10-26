package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

type Config struct {
	Namespaces []string
	CrGroup string
	CrVersion string
	CrKind string
	Port int
	UserIdLabel string
}

func NewConfigFromEnv(prefix string) (Config, error) {
	config := Config{}

	namespaces := []string{}
	for _, namespace := range strings.Split(os.Getenv(fmt.Sprintf("%sNAMESPACES", prefix)), ",") {
		namespaces = append(namespaces, strings.TrimSpace(namespace))
	}
	if len(namespaces) < 1 {
		return Config{}, fmt.Errorf("invalid configuration, need at least 1 namespace, got %d", len(namespaces))
	}
	config.Namespaces = namespaces
	
	if crGroup, ok := os.LookupEnv(fmt.Sprintf("%sCR_GROUP", prefix)); ok {
		config.CrGroup = crGroup
	} else {
		return Config{}, fmt.Errorf("invalid configuration, %sCR_GROUP must be provided", prefix)
	}
	
	if crVersion, ok := os.LookupEnv(fmt.Sprintf("%sCR_VERSION", prefix)); ok {
		config.CrVersion = crVersion
	} else {
		return Config{}, fmt.Errorf("invalid configuration, %sCR_VERSION must be provided", prefix)
	}
	
	if crKind, ok := os.LookupEnv(fmt.Sprintf("%sCR_KIND", prefix)); ok {
		config.CrKind = crKind
	} else {
		return Config{}, fmt.Errorf("invalid configuration, %sCR_KIND must be provided", prefix)
	}

	if port, ok := os.LookupEnv(fmt.Sprintf("%sPORT", prefix)); ok {
		portInt, err := strconv.Atoi(port)
		if err != nil {
			return Config{}, fmt.Errorf("invalid configuration, cannot coverrt port %s to integer: %w", port, err)
		}
		config.Port = portInt
	} else {
		return Config{}, fmt.Errorf("invalid configuration, %sCR_PORT must be provided", prefix)
	}

	if userIdLabel, ok := os.LookupEnv(fmt.Sprintf("%sUSER_ID_LABEL", prefix)); ok {
		config.UserIdLabel = userIdLabel
	} else {
		return Config{}, fmt.Errorf("invalid configuration, %sUSER_ID_LABEL must be provided", prefix)
	}
	
	return config, nil
}