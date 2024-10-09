import os
import logging
import json
from dataclasses import dataclass, field
import traceback

@dataclass
class Config:
    count_indexable_texts: int
    count_unindexed_texts: int
    version: str = field(default_factory=lambda: Config.get_ray_on_golem_version())
    texts_per_worker: int = field(default=None)
    network: str = field(default=None)

    METADATA_FILE_PATH: str = "config_metadata.json"

    _initializing: bool = field(default=True, init=False)

    def __post_init__(self):
        self.load_metadata()
        self.load_from_json()
        self.enforce_defaults()
        self._initializing = False
        logging.debug(f"Config initialized with count_indexable_texts: {self.count_indexable_texts}, count_unindexed_texts: {self.count_unindexed_texts}")

    @property
    def json_file_path(self):
        """Determine the JSON file path based on the network."""
        return f"config_{self.network.lower()}.json"

    @property
    def path_to_yaml(self):
        return f"golem-cluster-{self.network.lower()}.yaml"

    @staticmethod
    def get_ray_on_golem_version():
        try:
            import importlib.metadata
            return importlib.metadata.version("ray_on_golem")
        except importlib.metadata.PackageNotFoundError:
            return "x.y.z"

    def load_from_json(self):
        """Load the configuration from a JSON file."""
        if os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'r') as json_file:
                config_dict = json.load(json_file)
                for key, value in config_dict.items():
                    if key not in ["count_indexable_texts", "count_unindexed_texts", "version"]:
                        setattr(self, key, value)
        else:
            logging.warning(f"JSON file {self.json_file_path} does not exist. Using default values.")
            self.load_defaults()

    def save_to_json(self):
        """Save the current configuration to a JSON file."""
        json_managed_attrs = ["texts_per_worker", "network"]
        config_dict = {k: v for k, v in self.__dict__.items() 
                       if k in json_managed_attrs}
        with open(self.json_file_path, 'w') as json_file:
            json.dump(config_dict, json_file, indent=4)

    def __setattr__(self, name, value):
        immutable_attrs = ["count_indexable_texts", "count_unindexed_texts", "version"]
        yaml_managed_attrs = ["max_workers", "min_mem_gib", "min_cpu_threads", 
                              "min_storage_gib", "max_cpu_per_hour_price", "max_env_per_hour_price"]
        
        if self._initializing or name == "_initializing":
            super().__setattr__(name, value)
        else:
            if name in immutable_attrs:
                logging.warning(f"Attempt to modify immutable attribute {name} ignored.")
            elif name in yaml_managed_attrs:
                self._write_to_yaml(name, value)
            else:
                super().__setattr__(name, value)
                self.save_to_json()

    def __getattr__(self, name):
        yaml_managed_attrs = ["max_workers", "min_mem_gib", "min_cpu_threads", 
                              "min_storage_gib", "max_cpu_per_hour_price", "max_env_per_hour_price"]
        if name in yaml_managed_attrs:
            return self._read_from_yaml(name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def enforce_defaults(self):
        """
        Ensures the YAML file has all values, updating it with loaded values or defaults if necessary.
        """
        logging.debug("enforce_defaults called")
        
        yaml_managed_attrs = ["max_workers", "min_mem_gib", "min_cpu_threads", 
                              "min_storage_gib", "max_cpu_per_hour_price", "max_env_per_hour_price"]
        
        for attr in yaml_managed_attrs:
            yaml_value = self._read_from_yaml(attr)
            logging.debug(f"Read value for {attr}: {yaml_value}")
            
            if yaml_value is None:
                default_value = self.defaults.get(self.network, {}).get(attr)
                if default_value is not None:
                    self._write_to_yaml(attr, default_value)
                    setattr(self, attr, default_value)
                    logging.debug(f"Set default value for {attr}: {default_value}")
            else:
                setattr(self, attr, yaml_value)
                logging.debug(f"Set attribute {attr} to value from YAML: {yaml_value}")

        logging.debug("enforce_defaults completed")

    def _read_from_yaml(self, key):
        if not os.path.exists(self.path_to_yaml):
            raise FileNotFoundError(f"YAML file {self.path_to_yaml} does not exist")

        with open(self.path_to_yaml, "r") as file:
            for line in file:
                stripped_line = line.strip()
                if not stripped_line.startswith("#") and stripped_line.startswith(key + ":"):
                    value = stripped_line.split(":", 1)[1].strip()
                    return value

        # If we've gone through the whole file without finding the key
        return None

    def _write_to_yaml(self, key, value):
        logging.debug(f"_write_to_yaml called for key {key}")
        logging.debug(''.join(traceback.format_stack()))

        if not os.path.exists(self.path_to_yaml):
            raise FileNotFoundError(f"YAML file {self.path_to_yaml} does not exist")

        updated = False
        new_lines = []

        with open(self.path_to_yaml, "r") as file:
            for line_number, line in enumerate(file, 1):
                stripped_line = line.strip()
                if not updated and not stripped_line.startswith("#") and stripped_line.startswith(key + ":"):
                    new_lines.append(f"{key}: {value}\n")
                    updated = True
                    logging.debug(f"Updated {key} to {value} in {self.path_to_yaml} at line {line_number}")
                else:
                    new_lines.append(line)

        if updated:
            with open(self.path_to_yaml, "w") as file:
                file.writelines(new_lines)
        else:
            logging.warning(f"Key '{key}' not found in YAML file {self.path_to_yaml}")
            return False

        return updated

    def save_metadata(self):
        """Save metadata such as the last used network."""
        metadata = {'last_used_network': self.network}
        with open(self.METADATA_FILE_PATH, 'w') as metadata_file:
            json.dump(metadata, metadata_file, indent=4)

    def load_metadata(self):
        """Load metadata such as the last used network and defaults."""
        if os.path.exists(self.METADATA_FILE_PATH):
            with open(self.METADATA_FILE_PATH, 'r') as metadata_file:
                metadata = json.load(metadata_file)
                self.network = metadata.get('last_used_network', self.network)
                self.defaults = metadata.get('defaults', {})
        else:
            logging.info(f"Metadata file {self.METADATA_FILE_PATH} does not exist. Using default network.")
            self.defaults = {}

    def load_defaults(self):
        """Load default values for the current network."""
        defaults = self.defaults.get(self.network, {})
        for key, value in defaults.items():
            setattr(self, key, value)