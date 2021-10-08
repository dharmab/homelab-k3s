# Kubernetes Lab

Lab environment for single-node Kubernetes research.

The operating system is Arch Linux. Docker, kubelet, kubeadm and kubectl are
installed from the Arch Linux repositories.

To set up the environment, set up a Python 3 virtualenv and install the
dependencies in `requirements.txt`:

```bash
pip install -r requirements.txt
```

To create and launch the lab VM for the first time, run `make lab-up`. This
will create a VM, apply an Ansible playbook to install packages and initialize
Kubernetes, restart the VM to apply upgrades and download a kubeconfig file
to `kubernetes/kubeconfig.yaml`. You can use this kubeconfig file to access
the Kubernetes API:

```bash
export KUBECONFIG=kubernetes/kubeconfig.yaml
kubectl get node
```

If you stop the VM, you can use `vm-up` to start it again. You only need to
run `make lab-up` if you destroy the VM and need to recreate it again.
