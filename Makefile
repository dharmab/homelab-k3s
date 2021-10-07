.PHONY: lab-up vm-up vm-provision vm-down vm-restart vm-destroy vm-shell kubeadm-init kubeadm-reset

lab-up: vm-up vm-provision vm-restart kubeadm-init

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
	vagrant ssh -c 'sudo kubeadm init --config /etc/kubernetes/kubeadm.yaml --ignore-preflight-errors=Swap,SystemVerification'

kubeadm-reset:
	vagrant ssh -c 'sudo kubeadm reset'
