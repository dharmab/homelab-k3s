# Arma 3

Dedicated server for [Arma 3](https://arma3.com/). 

## Architecture

The [server](https://community.bistudio.com/wiki/Arma_3:_Dedicated_Server) runs as the single-replica `arma3` StatefulSet in the `arma3` Namespace. A [headless client](https://community.bistudio.com/wiki/Arma_3:_Headless_Client) runs as the `arma3-headless-client` StatefulSet in the same Namespace. The server is the primary process that runs the dedicated server. The headless client runs a virtual client which can offload AI processing; this can improve AI performance because Arma 3 has poor multithreading support within a single server process.

The Pod in each StatefulSet first runs an `install` init container which uses the `steamcmd` tool to authenticate to Steam's servers and download the Arma 3 dedicated server to a persistent volume. The server is therefore updated whenever the Pod is initialized. The Pod then mounts the same persistent volume into another container and runs the server executable.

A `steamcmd` sidecar container runs alongside the main `arma3` container in each Pod. This provides a convenient environment for downloading mods from the Steam Workshop. (If mods were installed by the init container, there would be a long delay in server startup time.)

The OnDelete upgrade strategy is used to avoid disruptive server restarts from trivial changes. Changes must be rolled out manually by deleting the Pod:

```sh
kubectl -n arma3 delete pod -l app.kubernetes.io/name=arma3
```

_Note that the server does not work in Vagrant because the Vagrant box's disk is too small to install the server._

## Configuration

There are three places the server can be configured:

- `server.cfg` is contained in the `server-config` Secret in the `arma3` namespace. It contains the content of the [server config file](https://community.bistudio.com/wiki/Arma_3:_Server_Config_File).
- `server.Arma3Profile` is contained in the `profiles` ConfigMap in the `arma3` Namespace. It contains the [server profile](https://community.bistudio.com/wiki/Arma_3:_Server_Profile) which configures custom difficulty settings.
- Mods such as ACE and ACRE are configured through CBA the [CBA Settings System](https://github.com/CBATeam/CBA_A3/wiki/CBA-Settings-System). By default, a server administrator can edit most settings in-game, but the settings will reset if the server process restarts. It is possible to configure these settings in an SQF file within a mission or a userconfig file on the server, but this may lock the settings from being edited by a server admin during gameplay.

## Administration

To log in as a server admin, type `#login <admin password>` into the in-game chat. A list of commands is available [on the wiki](https://community.bistudio.com/wiki/Multiplayer_Server_Commands).


## Mods

Mods can be configured in the lab config file using the `arma3.mods` option. To install or update all configured mods, stop any currently running mission, then run:

```
make cluster-deploy update-arma3-mods
kubectl -n arma3 delete pod -l app.kubernetes.io/name=arma3
```

You can verify the mod was loaded in the `arma3` container logs. A table will be printed on startup of all configured mods and their statuses.

## Troubleshooting

### Logs

To view logs of the init container that downloads the server:

```
kubectl -n arma3 logs statefulset/arma3 -c install
```

To follow the server logs:

```
kubectl -n arma3 logs statefulset/arma3 -c arma3 -f
```
