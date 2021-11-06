# NGINX Ingress Controller

The [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/) is a reference implementation of an [Ingress Controller](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers) that uses the [nginx](https://nginx.org) proxy server.

The controller runs as the `ingress-nginx-controller` Deployment in the `ingress-nginx` Namespace. Additionally, two Jobs are run to set up a validating and mutating admission webhook.

The controller Pods expose nginx ingresses on container ports 80/TCP and 443/TCP for HTTP and HTTPS, respectively. The `ingress-nginx-controller` Server maps these to the frontend NodePorts 31080/TCP and 31443/TCP, respectively.

## Usage

### Accessing Nginx

In the Vagrant environment, you can access Nginx at http://localhost:8080. Note that the root will respond with an HTTP 404 Not Found response. However, other components are exposed through nginx at various URL paths (as documented in their articles).

### Exposing Ingresses

To expose a service through nginx, create an Ingress that references the `nginx` Ingress Class and the Service and backend port to be proxied. The following Ingress that forwards requests under the `/example` path to the `example-service` Service in the `example-namespace` Namespace:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  namespace: example-namespace
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - pathType: Prefix
        path: /example
        backend:
          service:
            name: example-service
            port:
              # Should match a port on example-server
    	      # Can define `name` instead, if preferred
              number: 80

```

## Troubleshooting

### Logs

Controller logs are available with `kubectl -n ingress-nginx logs deployment/ingress-nginx-controller`. This includes the logs from the controller itself as well as the nginx access logs.

### Metrics

The `ingress-nginx` ServiceMonitor configures metrics scraping from the controller. Key metrics:


