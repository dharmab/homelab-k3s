# Longhorn

[Longhorn](https://longhorn.io) provides persistent storage. It runs multiple components in the `longhorn-system` Namepsace. Key components include:

- The `longhorn-manager` DaemonSet, which manages Kubernetes Volumes and engines. It also serves APIs for the UI and plugins
- The `longhorn-ui` Deployment, which serves an administrative web UI
- Multiple Deployments prefixed with `csi-`, which are microservices that provide the Container Storage Interface (CSI) plugin
- Multiple DaemonSets prefixed with  `engine-`, which are controllers for each volume on the Linux nodes

See [the upstream architecture documentation](https://longhorn.io/docs/latest/concepts) for details. Note that on Arch Linux, the `open-iscsi` package must be installed and the `iscsid` systemd service running for Longhorn to function.

## Usage

Longhorn provides the `longhorn` [Storage Class](https://kubernetes.io/docs/concepts/storage/storage-classes) for use in Pod templates and Persistent Volumes.

## Troubleshooting

### Logs

#### `failed to attach`

`csi-attacher` logs similar to the following may indicate that the `iscsid` service on the Node is not running:

```
Error processing "csi-413955cda71f7f9d580abe9afac233f654fdc5323fa9bb196f8b8d10c7b7afa1": failed to attach: rpc error: code = DeadlineExceeded desc = volume pvc-6e47b98a-3d98-4dc5-afc6-77dfbf553a65 failed to attach to node archlinux
```

### Metrics
