package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"path/filepath"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/selection"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/dynamic/dynamicinformer"
	"k8s.io/client-go/rest"
	k8sCache "k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

type Cache struct {
	lister    k8sCache.GenericLister
	informer  k8sCache.SharedIndexInformer
	namespace string
	userIdLabel string
}

type GenericResource struct {
	metav1.TypeMeta   `json:",inline"`
	Metadata metav1.ObjectMeta `json:"metadata"`
	Spec json.RawMessage `json:"spec"`
	Status json.RawMessage `json:"status,omitempty"`
}

// Synchronize the informer cache.
func (c *Cache) synchronize(ctx context.Context, doneCh chan bool) {
	if !k8sCache.WaitForCacheSync(ctx.Done(), c.informer.HasSynced) {
		doneCh <- false
	}
	doneCh <- true
}

// Run the informer.
func (c *Cache) run(ctx context.Context) {
	c.informer.Run(ctx.Done())
}

func (c *Cache) getAll() ([]runtime.Object, error) {
	output, err := c.lister.List(labels.NewSelector())
	if err != nil {
		return nil, fmt.Errorf("could not list servers for namespace %s: %w", c.namespace, err)
	}
	return output, nil
}
 
func (c *Cache) getByUserId(userId string) ([]runtime.Object, error) {
	selector := labels.NewSelector()
	if userId != "" {
		requirement, err := labels.NewRequirement(c.userIdLabel, selection.Equals, []string{userId})
		if err != nil {
			return nil, fmt.Errorf("could not set up selector when looking for servers for userId %s: %w", userId, err)
		}
		selector = selector.Add(*requirement)
	}
	output, err := c.lister.List(selector)
	if err != nil {
		return nil, fmt.Errorf("could not list servers for userId %s: %w", userId, err)
	}
	return output, nil
}

func (c *Cache) getByName(name string) (runtime.Object, error) {
	output, err := c.lister.Get(fmt.Sprintf("%s/%s", c.namespace, name))
	if err != nil {
		return nil, err
	}
	return output, nil
}

func (c *Cache) getByNameAndUserId(name string, userId string) (runtime.Object, error) {
	output, err := c.getByName(name)
	if err != nil {
		return nil, err
	}
	outputUnstructured, err := runtime.DefaultUnstructuredConverter.ToUnstructured(output)
	if err != nil {
		return nil, fmt.Errorf("could not convert server %s to unstructured: %w", name, err)
	}
	outputTyped := GenericResource{}
	err = runtime.DefaultUnstructuredConverter.FromUnstructured(outputUnstructured, &outputTyped)
	if err != nil {
		return nil, fmt.Errorf("could not parse metadata on server %s: %w", name, err)
	}
	if outputTyped.Metadata.Labels[c.userIdLabel] != userId {
		return nil, nil
	}
	return output, nil
}

func NewCacheFromConfig(ctx context.Context, config Config, namespace string) (*Cache, error) {
	var err error
	var clientConfig *rest.Config
	clientConfig, err = rest.InClusterConfig()
	if err != nil {
		log.Println("Cannot setup in-cluster config, looking for kubeconfig file")
		var kubeconfig *string
		if home := homedir.HomeDir(); home != "" {
			kubeconfig = flag.String("kubeconfig", filepath.Join(home, ".kube", "config"), "(optional) absolute path to the kubeconfig file")
		} else {
			kubeconfig = flag.String("kubeconfig", "", "absolute path to the kubeconfig file")
		}
		flag.Parse()

		clientConfig, err = clientcmd.BuildConfigFromFlags("", *kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("cannot setup k8s client config: %w", err)
		}
	}
	clusterClient, err := dynamic.NewForConfig(clientConfig)
	if err != nil {
		return nil, fmt.Errorf("cannot setup k8s dynamic client: %w", err)
	}

	resource := schema.GroupVersionResource{Group: config.CrGroup, Version: config.CrVersion, Resource: config.CrPlural}
	factory := dynamicinformer.NewFilteredDynamicSharedInformerFactory(clusterClient, time.Minute, namespace, nil)
	informer := factory.ForResource(resource).Informer()
	lister := factory.ForResource(resource).Lister()
	output := &Cache{informer: informer, lister: lister, namespace: namespace, userIdLabel: config.UserIdLabel}

	return output, nil
}
