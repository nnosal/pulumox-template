import pulumi, os

class BaseProvider:

    VALID_PROVIDER_KEYS = {'endpoint', 'username', 'password'}

    def __init__(self, name: str, config: dict) -> None:
        """Initialize the base provider with name and configuration.
        Args:
            name: Unique name for the provider resource
            config: Dictionary containing provider configuration
        """
        if self.set_config(config):
            self.provider = pulumi.Provider( resource_name=name, **self.config )
            self.set_default_ssh_keys()
        return self.provider

    def set_default_ssh_keys(self) -> None:
      """Load SSH keys from environment variable."""
      self.ssh_keys_vm = os.getenv( 'SSH_KEYS', [] )

    def set_config(self, config: dict) -> None:
        """Validate configuration against allowed keys."""
        config_keys = set(config.keys())
        invalid_keys = config_keys - self.VALID_PROVIDER_KEYS
        if invalid_keys:
            invalid_keys_str = ', '.join(map(repr, invalid_keys))
            raise ValueError(
                f"Configuration contains invalid keys: {invalid_keys_str}"
            )
        else:
          self.config = config

if __name__ == "__main__":
    pass
