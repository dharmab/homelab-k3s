# Arma 3

Dedicated server for Arma 3. 


## Architecture

The server runs as the single-replica `arma3` StatefulSet in the `arma3`. 

The Pod first runs an init container which uses the `steamcmd` tool to authenticate to Steam's servers and download the Arma 3 dedicated server to a persistent volume. The server is therefore updated whenever the Pod is initialized. The Pod then mounts the same persistent volume into another container and runs the server executable.

The OnDelete upgrade strategy is used to avoid disruptive server restarts from trivial changes. Changes must be rolled out manually by deleting the Pod:

```sh
kubectl -n arma3 delete pod -l app.kubernetes.io/name=arma3
```

_Note that the server does not work in Vagrant because the Vagrant box's disk is too small to install the server._

## Troubleshooting

### Logs

To view logs of the init container:

```
kubectl -n arma3 logs statefulset/arma3 -c steamcmd
```

To follow the server logs:

```
kubectl -n arma3 logs statefulset/arma3 -c arma3 -f
```
