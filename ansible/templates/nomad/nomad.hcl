datacenter = "{{ nomad_datacenter }}"

addresses {
  rpc = 127.0.0.1
  serf = 127.0.0.1
}
bind_addr = "0.0.0.0"
data_dir = "/opt/nomad"
disable_update_check = true

server {
  enabled = true
  bootstrap_expect = 1
}

client {
  enabled = true
}

telemetry {
  collection_interval = "1s"
  disable_hostname = true
  prometheus_metrics = true
  publish_allocation_metrics = true
  publish_node_metrics = true
}
