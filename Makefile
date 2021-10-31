.PHONY: lab-up vm-up vm-provision vm-down vm-restart vm-destroy vm-shell clean cluster-deploy format check

KUBECONFIG=kubernetes/kubeconfig.yaml

lab-up: clean install-dependencies vm-up vm-provision vm-restart $(KUBECONFIG) cluster-deploy

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

cluster-deploy:
	poetry run ./src/main.py deploy -m deploy/

clean:
	rm -f $(KUBECONFIG)

format:
	black **/*.py
	isort **/*.py

check:
	black --check **/*.py
	isort --check **/*.py
	mypy **/*.py
	pylint **/*.py
