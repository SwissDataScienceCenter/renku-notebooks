package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
)

// Config contains the basic conciguration for a server cache.
type Config struct {
	Namespaces  []string
	CrGroup     string
	CrVersion   string
	CrPlural    string
	Port        int
	UserIDLabel string
}

// NewConfigFromEnvOrDie generates a new configuration from environment variables.
// If the values are missing the program will exit with exit code 1. There is no way
// to recover from this error and this is crucial for the cache server to run.
func NewConfigFromEnvOrDie(prefix string) Config {
	config := Config{}
	var namespaces []string
	log.Printf("Environment variable prefix is '%s'\n", prefix)
	err := json.Unmarshal([]byte(os.Getenv(fmt.Sprintf("%sNAMESPACES", prefix))), &namespaces)
	if err != nil {
		log.Fatalf("Cannot parse namespaces %s in config to json: %v\n", os.Getenv(fmt.Sprintf("%sNAMESPACES", prefix)), err)
	}
	if len(namespaces) < 1 {
		log.Fatalf("Invalid configuration, need at least 1 namespace, got %d\n", len(namespaces))
	}
	config.Namespaces = namespaces

	if crGroup, ok := os.LookupEnv(fmt.Sprintf("%sCR_GROUP", prefix)); ok {
		config.CrGroup = crGroup
	} else {
		log.Fatalf("Invalid configuration, %sCR_GROUP must be provided\n", prefix)
	}

	if crVersion, ok := os.LookupEnv(fmt.Sprintf("%sCR_VERSION", prefix)); ok {
		config.CrVersion = crVersion
	} else {
		log.Fatalf("invalid configuration, %sCR_VERSION must be provided", prefix)
	}

	if crPlural, ok := os.LookupEnv(fmt.Sprintf("%sCR_PLURAL", prefix)); ok {
		config.CrPlural = crPlural
	} else {
		log.Fatalf("invalid configuration, %sCR_PLURAL must be provided", prefix)
	}

	if port, ok := os.LookupEnv(fmt.Sprintf("%sPORT", prefix)); ok {
		portInt, err := strconv.Atoi(port)
		if err != nil {
			log.Fatalf("Invalid configuration, cannot coverrt port %s to integer: %v\n", port, err)
		}
		config.Port = portInt
	} else {
		log.Fatalf("Invalid configuration, %sPORT must be provided\n", prefix)
	}

	if userIDLabel, ok := os.LookupEnv(fmt.Sprintf("%sUSER_ID_LABEL", prefix)); ok {
		config.UserIDLabel = userIDLabel
	} else {
		log.Fatalf("Invalid configuration, %sUSER_ID_LABEL must be provided\n", prefix)
	}

	return config
}
