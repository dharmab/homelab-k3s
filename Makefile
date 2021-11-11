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
	poetry run ./lab/kubeconfig.py --kubeconfig $(KUBECONFIG)

cluster-deploy:
	poetry run ./lab/main.py -c $(LABCONFIG) deploy -m deploy/

cluster-test:
	poetry run pytest tests/ -m integration

clean:
	rm -f $(KUBECONFIG)

format:
	@echo "Formatting Python"
	isort **/*.py
	black **/*.py
	@echo "Formatting YAML"
	find . '(' -name "*.yml" -or -name "*.yaml" ')' -exec yamlfmt {} --write ';'
	@echo "All formatting completed"

check:
	@echo "Checking Python formatting"
	black --check **/*.py
	isort --check **/*.py
	@echo "Checking Python type hints"
	mypy **/*.py
	@echo "Checking Python style"
	pylint **/*.py
	@echo "Checking all YAML filenames end in .yaml rather than .yml"
	! find . -name *.yml | grep .
	@echo "Checking YAML style"
	yamllint .
	@echo "Checking Ansible playbook style"
	ansible-lint -qq ansible/main.yaml
	@echo "All checks passed"
