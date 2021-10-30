.PHONY: lab-up vm-up vm-provision vm-down vm-restart vm-destroy vm-shell clean

KUBECONFIG=kubernetes/kubeconfig.yaml

lab-up: clean install-dependencies vm-up vm-provision vm-restart $(KUBECONFIG)

install-dependencies:
	poetry install --no-root

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

$(KUBECONFIG): install-dependencies
	vagrant ssh -c "sudo cat /etc/rancher/k3s/k3s.yaml" > $(KUBECONFIG)
	poetry run ./hack/kubeconfig.py --kubeconfig $(KUBECONFIG)

clean:
	rm -f $(KUBECONFIG)
