Vagrant.configure("2") do |config|
  config.vm.box = "archlinux/archlinux"
  # Kubernetes API
  config.vm.network "forwarded_port", protocol: "tcp", guest: 6443, host: 6443
  # Nginx HTTP/S
  config.vm.network "forwarded_port", protocol: "tcp", guest: 80, host: 8080
  config.vm.network "forwarded_port", protocol: "tcp", guest: 443, host: 8443
  # Teamspeak voice and filetransfer
  # Note that libvirt doesn't actually support UDP: https://github.com/vagrant-libvirt/vagrant-libvirt/issues/260
  config.vm.network "forwarded_port", protocol: "udp", guest: 31987, host: 9987
  config.vm.network "forwarded_port", protocol: "tcp", guest: 38988, host: 10011
  config.vm.provider "libvirt" do |v|
    v.cpus = 4
    v.memory = 8192
  end
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "ansible/main.yaml"
  end
end
