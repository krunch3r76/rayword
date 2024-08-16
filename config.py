from collections import namedtuple
import os
import logging

BaseConfig = namedtuple(
    "BaseConfig",
    [
        "version",
        "texts_per_worker",
        "network",
        "count_indexable_texts",
        "count_unindexed_texts",
    ],
)

key_to_yaml_key = {
    "max_workers": "max_workers",
    "minimum_memory": "min_mem_gib",
    "minimum_cpu_threads": "min_cpu_threads",
    "minimum_storage": "min_storage_gib",
    "max_cpu_per_hour_price": "max_cpu_per_hour_price",
    "max_env_per_hour_price": "max_env_per_hour_price",
}


class Config(BaseConfig):
    @property
    def path_to_yaml(self):
        if self.network == "MAINNET":
            return "golem-cluster-mainnet.yaml"
        else:
            return "golem-cluster-testnet.yaml"

    def __getattr__(self, name):
        if name in key_to_yaml_key:
            return self._read_from_yaml(key_to_yaml_key[name])
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        try:
            if name in key_to_yaml_key:
                self._write_to_yaml(name, key_to_yaml_key[name])
            else:
                super().__setattr__(name, value)
        except Exception as e:
            logging.debug(f"{e}...... {name} - > {value}")

    def _read_from_yaml(self, key):
        if not os.path.exists(self.path_to_yaml):
            raise FileNotFoundError(f"YAML file {self.path_to_yaml} does not exist")
        with open(self.path_to_yaml, "r") as file:
            lines = file.readlines()
            for line in lines:
                if line.strip().startswith(key):
                    return line.split(":", 1)[1].strip()
        return None  # Return none if the key is not found

    def _write_to_yaml(self, key, value):
        updated = False
        if not os.path.exists(self.path_to_yaml):
            raise FileNotFoundError(f"YAML file {self.path_to_yaml} does not exist")

        with open(self.path_to_yaml, "r") as file:
            lines = file.readlines()

        with open(f"/tmp/{self.path_to_yaml}", "w") as file:
            for line in lines:
                if line.startswith("key"):
                    file.write(f"{key}: {value}\n")

        # kludge, instead of copying make sure the write to the temp succeeded then write over
        with open(f"{self.path_to_yaml}", "w") as file:
            for line in lines:
                if line.startswith("key"):
                    file.write(f"{key}: {value}\n")

        if not updated:
            raise Exception(f"key {key} not found in yaml {self.path_to_yaml}")

    # @property
    # def max_workers(self):
