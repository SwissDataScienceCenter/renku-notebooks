package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"
)

// Config contains the basic conciguration for a server cache.
type Config struct {
	// A list of k8s namespaces where resources will be cached and watched for.
	Namespaces []string
	// The group of the k8s resource that should be cached.
	CrGroup string
	// The version of the k8s resource that should be cached.
	CrVersion string
	// The plural name of the k8s resource that should be cached.
	CrPlural string
	// The group of the AmaltheaSession resource that should be cached.
	AmaltheaSessionGroup string
	// The version of the AmaltheaSession resource that should be cached.
	AmaltheaSessionVersion string
	// The plural name of the AmaltheaSession resource that should be cached.
	AmaltheaSessionPlural string
	// The group of the ShipwrightBuildRun resource that should be cached.
	ShipwrightBuildRunGroup string
	// The version of the ShipwrightBuildRun resource that should be cached.
	ShipwrightBuildRunVersion string
	// The plural name of the ShipwrightBuildRun resource that should be cached.
	ShipwrightBuildRunPlural string
	// The group of the TektonTaskRun resource that should be cached.
	TektonTaskRunGroup string
	// The version of the TektonTaskRun resource that should be cached.
	TektonTaskRunVersion string
	// The plural name of the TektonTaskRun resource that should be cached.
	TektonTaskRunPlural string
	// The port where the server will listen to for providing responses to requests
	// about listing the cached resources or for returning specific resources.
	Port int
	// The lable on the resources that identifies a specific user. This is used in the
	// endpoints where the cache server will list resources that belong to a specific user.
	// This is determined solely by a label selector on the specific label name specified
	// in the parameters below. The value that this key should match is passed as a path parameter in
	// the http requests.
	AmaltheaSessionUserIDLabel string
	JupyterServerUserIDLabel   string
	UserIDLabel                string
	// The maximum duration to wait for all caches to sync.
	CacheSyncTimeout time.Duration
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

	if asGroup, ok := os.LookupEnv(fmt.Sprintf("%sAMALTHEA_SESSION_GROUP", prefix)); ok {
		config.AmaltheaSessionGroup = asGroup
	} else {
		config.AmaltheaSessionGroup = "amalthea.dev"
	}

	if asVersion, ok := os.LookupEnv(fmt.Sprintf("%sAMALTHEA_SESSION_VERSION", prefix)); ok {
		config.AmaltheaSessionVersion = asVersion
	} else {
		config.AmaltheaSessionVersion = "v1alpha1"
	}

	if asPlural, ok := os.LookupEnv(fmt.Sprintf("%sAMALTHEA_SESSION_PLURAL", prefix)); ok {
		config.AmaltheaSessionPlural = asPlural
	} else {
		config.AmaltheaSessionPlural = "amaltheasessions"
	}

	if brGroup, ok := os.LookupEnv(fmt.Sprintf("%sSHIPWRIGHT_BUILDRUN_GROUP", prefix)); ok {
		config.ShipwrightBuildRunGroup = brGroup
	} else {
		config.ShipwrightBuildRunGroup = "shipwright.io"
	}

	if brVersion, ok := os.LookupEnv(fmt.Sprintf("%sSHIPWRIGHT_BUILDRUN_VERSION", prefix)); ok {
		config.ShipwrightBuildRunVersion = brVersion
	} else {
		config.ShipwrightBuildRunVersion = "v1beta1"
	}

	if brPlural, ok := os.LookupEnv(fmt.Sprintf("%sSHIPWRIGHT_BUILDRUN_PLURAL", prefix)); ok {
		config.ShipwrightBuildRunPlural = brPlural
	} else {
		config.ShipwrightBuildRunPlural = "buildruns"
	}

	if trGroup, ok := os.LookupEnv(fmt.Sprintf("%sTEKTON_TASKRUN_GROUP", prefix)); ok {
		config.TektonTaskRunGroup = trGroup
	} else {
		config.TektonTaskRunGroup = "tekton.dev"
	}

	if trVersion, ok := os.LookupEnv(fmt.Sprintf("%sTEKTON_TASKRUN_VERSION", prefix)); ok {
		config.TektonTaskRunVersion = trVersion
	} else {
		config.TektonTaskRunVersion = "v1"
	}

	if trPlural, ok := os.LookupEnv(fmt.Sprintf("%sTEKTON_TASKRUN_PLURAL", prefix)); ok {
		config.TektonTaskRunPlural = trPlural
	} else {
		config.TektonTaskRunPlural = "taskruns"
	}

	if port, ok := os.LookupEnv(fmt.Sprintf("%sPORT", prefix)); ok {
		portInt, err := strconv.Atoi(port)
		if err != nil {
			log.Fatalf("Invalid configuration, cannot covert port %s to integer: %v\n", port, err)
		}
		if portInt <= 0 {
			log.Fatalf("Invalid configuration, port cannot be <= 0, got %d\n", portInt)
		}
		config.Port = portInt
	} else {
		log.Fatalf("Invalid configuration, %sPORT must be provided\n", prefix)
	}

	if userIDLabel, ok := os.LookupEnv(fmt.Sprintf("%sJUPYTER_SERVER_USER_ID_LABEL", prefix)); ok {
		config.JupyterServerUserIDLabel = userIDLabel
	} else {
		config.JupyterServerUserIDLabel = "renku.io/userId"
	}

	if userIDLabel, ok := os.LookupEnv(fmt.Sprintf("%sAMALTHEA_SESSION_USER_ID_LABEL", prefix)); ok {
		config.AmaltheaSessionUserIDLabel = userIDLabel
	} else {
		config.AmaltheaSessionUserIDLabel = "renku.io/safe-username"
	}

	if userIDLabel, ok := os.LookupEnv(fmt.Sprintf("%sUSER_ID_LABEL", prefix)); ok {
		config.UserIDLabel = userIDLabel
	} else {
		config.UserIDLabel = "renku.io/safe-username"
	}

	if cacheSyncTimeoutSeconds, ok := os.LookupEnv(fmt.Sprintf("%sCACHE_SYNC_TIMEOUT_SECONDS", prefix)); ok {
		cacheSyncTimeoutSecondsInt, err := strconv.Atoi(cacheSyncTimeoutSeconds)
		if err != nil {
			log.Fatalf("Invalid configuration, cannot covert cache sync timeout seconds %s to integer: %v\n", cacheSyncTimeoutSeconds, err)
		}
		if cacheSyncTimeoutSecondsInt <= 0 {
			log.Fatalf("Invalid configuration, cache sync timeout seconds cannot be <= 0, got %d\n", cacheSyncTimeoutSecondsInt)
		}
		config.CacheSyncTimeout = time.Duration(time.Second * time.Duration(cacheSyncTimeoutSecondsInt))
	} else {
		config.CacheSyncTimeout = time.Duration(time.Second * 600)
	}

	return config
}
