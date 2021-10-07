.PHONY: vm-up vm-down vm-destroy vm-shell

vm-up:
	vagrant up --provider=libvirt

vm-down:
	vagrant halt

vm-restart: vm-down vm-up

vm-destroy:
	vagrant destroy

vm-shell:
	@vagrant ssh
