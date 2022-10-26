package main

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"path/filepath"
	"sync"

	// coreV1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/kubernetes/scheme"
	_ "k8s.io/client-go/plugin/pkg/client/auth"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

type LocalServerData struct {
	m       sync.Mutex
	servers map[types.UID](*JupyterServer)
}

const GroupName = "amalthea.dev"
const GroupVersion = "v1alpha1"

var (
	SchemeGroupVersion = schema.GroupVersion{Group: GroupName, Version: GroupVersion}
	SchemeBuilder      = runtime.NewSchemeBuilder(addKnownTypes)
	AddToScheme        = SchemeBuilder.AddToScheme
	namespace          = "renku"
	localServerData    *LocalServerData
)

type JSClient struct {
	restClient rest.Interface
}

func addKnownTypes(scheme *runtime.Scheme) error {
	scheme.AddKnownTypes(SchemeGroupVersion,
		&JupyterServer{},
		&JupyterServerList{},
	)

	metav1.AddToGroupVersion(scheme, SchemeGroupVersion)
	return nil
}

func NewForConfig(c *rest.Config) (*JSClient, error) {
	config := *c
	config.ContentConfig.GroupVersion = &schema.GroupVersion{Group: GroupName, Version: GroupVersion}
	config.APIPath = "/apis"
	config.NegotiatedSerializer = scheme.Codecs.WithoutConversion()
	config.UserAgent = rest.DefaultKubernetesUserAgent()

	client, err := rest.RESTClientFor(&config)
	if err != nil {
		return nil, err
	}

	return &JSClient{restClient: client}, nil
}

func (s *LocalServerData) Update(js *JupyterServer) {
	s.m.Lock()
	s.servers[js.ObjectMeta.UID] = js
	s.m.Unlock()
}

func (s *LocalServerData) GetServers() []JupyterServer {
	s.m.Lock()
	list := []JupyterServer{}
	for _, j := range s.servers {
		list = append(list, *j)
	}
	s.m.Unlock()
	return list
}

func (c *JSClient) JupyterServers(namespace string) JupyterServerInterface {
	return &jupyterServerClient{
		restClient: c.restClient,
		ns:         namespace,
	}
}

func initializeServers(j *JupyterServerList) {
	for _, s := range j.Items {
		localServerData.Update(&s)
	}
}

func getServers(w http.ResponseWriter, r *http.Request) {
	result := localServerData.GetServers()
	log.Printf("got /server request - returning %v objects\n", len(result))
	jsonResponse, _ := json.Marshal(result)
	io.WriteString(w, string(jsonResponse))
}

func startHHTTPServer() {
	http.HandleFunc("/servers", getServers)

	// start http server on port 3333
	err := http.ListenAndServe(":3333", nil)
	if err != nil {
		log.Printf("Unable to start http server")
	}
}

func main() {

	// generate configuration info
	var home = homedir.HomeDir()
	var kubeconfig = filepath.Join(home, ".kube", "config")
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		panic(err.Error())
	}

	AddToScheme(scheme.Scheme)

	clientSet, err := NewForConfig(config)
	if err != nil {
		panic(err)
	}

	// initialize local data
	localServerData = &(LocalServerData{})
	localServerData.servers = make(map[types.UID](*JupyterServer))

	jupyterServers, err := clientSet.JupyterServers(namespace).List(metav1.ListOptions{})
	if err != nil {
		panic(err)
	}

	log.Printf("Initializing servers...")
	initializeServers(jupyterServers)

	log.Printf("Starting HTTP server...")
	go startHHTTPServer()

	resourceVersion := jupyterServers.ListMeta.ResourceVersion

	// SETUP WATCHER CHANNEL
	log.Printf("Starting watcher...")
	watcher, err := clientSet.JupyterServers(namespace).Watch(v1.ListOptions{ResourceVersion: resourceVersion})
	if err != nil {
		panic(err.Error())
	}
	ch := watcher.ResultChan()

	for {
		event := <-ch
		localJupyterServer := event.Object.(*JupyterServer)

		log.Printf(
			"Event = %v, name, id = %v, %v\n",
			event.Type,
			localJupyterServer.ObjectMeta.Name,
			localJupyterServer.ObjectMeta.UID,
		)
		log.Printf(
			"Annotations = %v, labels = %v\n",
			localJupyterServer.ObjectMeta.Annotations,
			localJupyterServer.ObjectMeta.Labels,
		)
		log.Printf("username = %v\n\n", localJupyterServer.ObjectMeta.Annotations["renku.io/username"])
		localServerData.Update(localJupyterServer)
	}
}
