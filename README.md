# Kubernetes Lab

Lab environment for single-node Kubernetes research.

The operating system is [Arch Linux](https://archlinux.org/) and the Kubernetes
distribution is [k3s](https://k3s.io) (binary installed from GitHub releases).

To set up the environment, install make, Python 3 and
[Poetry](https://python-poetry.org/).

To create and launch the lab VM for the first time, run `make lab-up`. This
will create a VM, apply an Ansible playbook to install packages and initialize
Kubernetes, restart the VM to apply upgrades and download a kubeconfig file
to `kubernetes/kubeconfig.yaml`. You can use this kubeconfig file to access
the Kubernetes API:

```sh
export KUBECONFIG=kubernetes/kubeconfig.yaml
kubectl get node
```

If you stop the VM, you can use `vm-up` to start it again. You only need to
run `make lab-up` if you destroy the VM and need to recreate it again.

- Uninstaller hooks
- Integration tests
- Documentation
- YAML linting and formatting
