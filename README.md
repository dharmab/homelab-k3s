# Kubernetes Lab

Lab environment for single-node Kubernetes research.

The operating system is Arch Linux. Docker, kubelet, kubeadm and kubectl are
installed from the Arch Linux repositories.

To create and launch the lab VM for the first time, run `make lab-up`. This
will create a VM, apply an Ansible playbook to install packages and upgrades,
restart the VM to apply upgrades, and then run `kubeadm init` to start
Kubernetes. 

If you stop the VM, you can use `vm-up` to start it again. You only need to
run `make lab-up` if you destroy the VM and need to recreate it again.
