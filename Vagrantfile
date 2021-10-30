Vagrant.configure("2") do |config|
  config.vm.box = "archlinux/archlinux"
  config.vm.network "forwarded_port", protocol: "tcp", guest: 4646, host: 4646
  config.vm.provider "libvirt" do |v|
    v.cpus = 4
    v.memory = 8192
  end
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "ansible/main.yaml"
    ansible.extra_vars = {
      nomad_datacenter: "vagrant",
    }
  end
end
