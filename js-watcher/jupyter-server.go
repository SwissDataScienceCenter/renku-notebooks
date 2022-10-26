package main

import (
	"context"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/rest"
)

// new types which are added to the k8s api
type JupyterServerSpec struct {
	Replicas int `json:"replicas"`
}

type JupyterServer struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec JupyterServerSpec `json:"spec"`
}

type JupyterServerList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`

	Items []JupyterServer `json:"items"`
}

// DeepCopyInto copies all properties of this object into another object of the
// same type that is provided as a pointer.
func (in *JupyterServer) DeepCopyInto(out *JupyterServer) {
	out.TypeMeta = in.TypeMeta
	out.ObjectMeta = in.ObjectMeta
	out.Spec = JupyterServerSpec{
		Replicas: in.Spec.Replicas,
	}
}

// DeepCopyObject returns a generically typed copy of an object
func (in *JupyterServer) DeepCopyObject() runtime.Object {
	out := JupyterServer{}
	in.DeepCopyInto(&out)

	return &out
}

// DeepCopyObject returns a generically typed copy of an object
func (in *JupyterServerList) DeepCopyObject() runtime.Object {
	out := JupyterServerList{}
	out.TypeMeta = in.TypeMeta
	out.ListMeta = in.ListMeta

	if in.Items != nil {
		out.Items = make([]JupyterServer, len(in.Items))
		for i := range in.Items {
			in.Items[i].DeepCopyInto(&out.Items[i])
		}
	}

	return &out
}

// interface which defines how to talk to k8s API using the
// standard conventions
type JupyterServerInterface interface {
	List(opts metav1.ListOptions) (*JupyterServerList, error)
	Get(name string, options metav1.GetOptions) (*JupyterServer, error)
	Create(*JupyterServer) (*JupyterServer, error)
	Watch(opts metav1.ListOptions) (watch.Interface, error)
	// ...
}

// a client which implements the JupyterServerInterface
type jupyterServerClient struct {
	restClient rest.Interface
	ns         string
}

func (c *jupyterServerClient) List(opts metav1.ListOptions) (*JupyterServerList, error) {
	result := JupyterServerList{}
	err := c.restClient.
		Get().
		Namespace(c.ns).
		Resource("jupyterServers").
		VersionedParams(&opts, scheme.ParameterCodec).
		Do(context.Background()).
		Into(&result)

	return &result, err
}

func (c *jupyterServerClient) Get(name string, opts metav1.GetOptions) (*JupyterServer, error) {
	result := JupyterServer{}
	err := c.restClient.
		Get().
		Namespace(c.ns).
		Resource("jupyterServers").
		Name(name).
		VersionedParams(&opts, scheme.ParameterCodec).
		Do(context.Background()).
		Into(&result)

	return &result, err
}

func (c *jupyterServerClient) Create(jupyterServer *JupyterServer) (*JupyterServer, error) {
	result := JupyterServer{}
	err := c.restClient.
		Post().
		Namespace(c.ns).
		Resource("jupyterServers").
		Body(jupyterServer).
		Do(context.Background()).
		Into(&result)

	return &result, err
}

func (c *jupyterServerClient) Watch(opts metav1.ListOptions) (watch.Interface, error) {
	opts.Watch = true
	return c.restClient.
		Get().
		Namespace(c.ns).
		Resource("jupyterServers").
		VersionedParams(&opts, scheme.ParameterCodec).
		Watch(context.Background())
}
