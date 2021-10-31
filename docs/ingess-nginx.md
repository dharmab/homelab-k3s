# NGINX Ingress Controller

The [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/) is a reference implementation of an [Ingress Controller](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers) that uses the [nginx](https://nginx.org) proxy server.

The controller runs as the `ingress-nginx-controller` Deployment in the `ingress-nginx` Namespace. Additionally, two Jobs are run to set up a validating and mutating admission webhook.

## Usage

## Troubleshooting

### Logs

Controller logs are available with `kubectl -n ingress-nginx logs deployment/ingress-nginx-controller`.

### Metrics
