.PHONY: lab-up vm-up vm-provision vm-down vm-restart vm-destroy vm-shell kubeadm-init kubeadm-reset

lab-up: clean vm-up vm-provision vm-restart kubernetes/kubeconfig.yaml

VAGRANT_UP=vagrant up --provider=libvirt --no-provision

vm-up:
	$(VAGRANT_UP)

vm-provision:
	vagrant provision

vm-down:
	vagrant halt

vm-restart:
	vagrant halt
	$(VAGRANT_UP)

vm-destroy:
	vagrant destroy

vm-shell:
	@vagrant ssh

kubeadm-init:
	vagrant ssh -c 'sudo kubeadm init \
		--config /etc/kubernetes/kubeadm.yaml \
		--apiserver-cert-extra-sans 127.0.0.1 \
		--skip-phases=addon/kube-proxy \
		--ignore-preflight-errors=Swap,SystemVerification'

kubeadm-reset:
	vagrant ssh -c 'sudo kubeadm reset'

SSH_CONFIG=vagrant/ssh_config

$(SSH_CONFIG):
	vagrant ssh-config > $(SSH_CONFIG)

KUBECONFIG=kubernetes/kubeconfig.yaml

$(KUBECONFIG): $(SSH_CONFIG)
	scp -F $(SSH_CONFIG) default:.kube/config $(KUBECONFIG)
	./hack/kubeconfig.py --kubeconfig $(KUBECONFIG)

.PHONY: clean

clean:
	rm -f $(SSH_CONFIG) $(KUBECONFIG)
