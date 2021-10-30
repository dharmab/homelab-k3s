Vagrant.configure("2") do |config|
  config.vm.box = "archlinux/archlinux"
  config.vm.network "forwarded_port", protocol: "tcp", guest: 6443, host: 6443
  config.vm.provider "libvirt" do |v|
    v.cpus = 2
    v.memory = 4096
  end
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "ansible/main.yaml"
  end
end
