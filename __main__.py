import pulumi, os, textwrap, requests
from src.provisionner.proxmox import ProxmoxProvider as Proxmox
from src.tools.file import LoadFile

if __name__ == "__main__":

  # Get Config + Connect to Proxmox...
  config = pulumi.Config('pulumox')
  proxmoxConfig = {
      "endpoint": config.require("pve_url"),
      "insecure": config.get_bool("pve_url_insecure") or False,
      "username": config.require("pve_username"),
      "password": config.require_secret("pve_password")
    }
  cluster = Proxmox(  name='default', config=proxmoxConfig )

  # Test
  cluster.provision( LoadFile().yaml('templates/_test/1.yml') )

  # ###############
  # ### WINDOWS ###
  # ###############
  #setupWindows(cluster)

  # #############
  # ### MACOS ###
  # #############
  #setupMacOS(cluster)

  # #############
  # ### LINUX ###
  # #############
  #setupLinux(cluster)
