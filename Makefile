.PHONY: lab-up vm-up vm-provision vm-down vm-restart vm-destroy vm-shell

lab-up: clean vm-up vm-provision vm-restart

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
