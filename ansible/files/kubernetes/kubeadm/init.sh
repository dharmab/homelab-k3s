#!/bin/bash

if [[ ! -f /etc/kubernets/admin.conf ]];
then
  if ! sudo kubeadm init --config /etc/kubernetes/kubeadm.yaml;
  then
    echo "An error occurred while attempting to run kubeadm init"
    exit 1
  fi
else
  echo "kubeadm init appears to have already been run. Skipping..."
fi

if ! mkdir -p "$HOME/.kube";
then
  echo "An error occurred while attempting to create the kubeconfig directory"
  exit 1
fi
if ! sudo cp -i /etc/kubernetes/admin.conf "$HOME/.kube/config";
then
  echo "An error occurred while attempting to copy the admin kubeconfig to the kubeconfig directory"
  exit 1
fi
if ! sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config";
then
  echo "An error occurred while attempting to modify permissions on the kubeconfig file"
  exit 1
fi
