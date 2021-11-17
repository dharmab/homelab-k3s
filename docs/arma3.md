# Arma 3

Dedicated server for [Arma 3](https://arma3.com/). 

## Architecture

The server runs as the single-replica `arma3` StatefulSet in the `arma3`. 

The Pod first runs an init container which uses the `steamcmd` tool to authenticate to Steam's servers and download the Arma 3 dedicated server to a persistent volume. The server is therefore updated whenever the Pod is initialized. The Pod then mounts the same persistent volume into another container and runs the server executable.

The OnDelete upgrade strategy is used to avoid disruptive server restarts from trivial changes. Changes must be rolled out manually by deleting the Pod:

```sh
kubectl -n arma3 delete pod -l app.kubernetes.io/name=arma3
```

_Note that the server does not work in Vagrant because the Vagrant box's disk is too small to install the server._

## Mods

Mod installation is not automated due to a segmentation fault issue in steamcmd when installing large workshop mods which causes large delays in server startup time. Mods can be installed and enabled manually.

In this example, we'll install and enable the [Community Base Addons](https://steamcommunity.com/sharedfiles/filedetails/?id=450814997) mod. Note the `id` parameter from the Steam Workshop URL (`450814997`).

Run the following command to download the CBA_A3 files under `/opt/arma3/steamapps/workshop/content`, rerunning it if it fails with a segmentation fault:

```sh
kubectl -n arma3 exec -it arma3-0 -c steamcmd -- bash -c 'steamcmd +login $STEAM_USERNAME $STEAM_PASSWORD +force_install_dir /opt/arma3 +workshop_download_item $ARMA3_APPID 450814997 +quit'
```

To make the mod visible to the Arma 3 server process, it needs to appear to be in a subdirectory of the `/opt/arma` that is prefixed with the `@` symbol. We can do this with a [symbolic link](https://man7.org/linux/man-pages/man2/symlink.2.html). Run the following command to create a symbolic link from `/opt/arma3/@cba_a3` to the mod content:

```sh
kubectl -n arma3 exec -it arma3-0 -c steamcmd -- bash -c 'ln -s /opt/arma3/steamapps/workshop/content/$ARMA3_APPID/450814997 /opt/arma3/@cba_a3'
```

Enable the mod by adding a `-mod=@cba_a3` argument to the `arma3` container in the `arma3` StatefulSet. (You can enable multiple mods by separating their paths with semicolons.) _Note that this step may need to be repeated if you deploy updated manifests using `deploy.py`._

```sh
kubectl -n arma3 edit statefulset arma3
```

Delete the running Pod to apply the changes:

```sh
kubectl -n arma3 delete pod -l app.kubernetes.io/name=arma3
```

You can verify the mod was loaded in the `arma3` container logs:

```
3:16:59                      Community Base Addons v3.15.6 |              @cba_a3 |      false |      false |             GAME DIR | 00127cc3983804656fcdb4021c85a778b920cb3d |  5ca1ed2c | /opt/arma3/@cba_a3
```

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
