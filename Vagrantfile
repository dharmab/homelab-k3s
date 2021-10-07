Vagrant.configure("2") do |config|
  config.vm.box = "archlinux/archlinux"
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "ansible/main.yaml"
  end
end
