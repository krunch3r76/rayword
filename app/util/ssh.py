# util/ssh.py

from dataclasses import dataclass
import subprocess
import logging
import shlex
import os


@dataclass
class SSHConfig:
    """
    A configuration class for establishing SSH connections to remote nodes.

    This class encapsulates the necessary parameters and options for creating
    an SSH connection, such as identity file, user and IP of the head node,
    and additional SSH options.

    Attributes:
        options (list): A list of SSH options (e.g., StrictHostKeyChecking=no).
        identity_file (str): Path to the SSH identity file (private key).
        head_user_and_ip (str): SSH username and IP address of the head node in the format 'user@ip'.
        source (str): The source path for SSH operations.

    Methods:
        ssh_arguments_str: Returns the SSH arguments as a single string for use in commands.
        ssh_arguments_list: Returns the SSH arguments as a list for use with subprocess.
    """

    options: list
    identity_file: str
    head_user_and_ip: str
    source: str

    @property
    def ssh_arguments_str(self):
        """
        Returns SSH arguments formatted as a single string.

        This property is useful for constructing SSH command strings for
        direct execution in a shell environment.

        Returns:
            str: SSH arguments formatted as a single string.
        """
        rv = f"-o {' -o '.join([shlex.quote(option) for option in self.options])} -i {shlex.quote(self.identity_file)}"
        logging.debug(rv)
        return rv

    @property
    def ssh_arguments_list(self):
        """
        Returns SSH arguments formatted as a list.

        This property is useful for constructing SSH command arguments for
        use with subprocess-like interfaces where arguments are passed as a list.

        Returns:
            list: SSH arguments formatted as a list, suitable for subprocess calls.
        """
        parameterized_option_list = []
        for option in self.options:
            parameterized_option_list.extend(["-o", option])
        parameterized_identity_file_list = ["-i", self.identity_file]
        return parameterized_option_list + parameterized_identity_file_list

    @staticmethod
    def parse_ssh_command(ssh_command_str):
        """
        Parses an SSH command string and creates an SSHConfig object.

        Args:
            ssh_command_str (str): An example SSH command to connect to a remote node.

        Returns:
            SSHConfig: The configured SSHConfig object.
        """
        invocation_args = ssh_command_str.split()[1:]  # Skipping the 'ssh' part
        arguments = shlex.split(" ".join(invocation_args))
        options = []

        for i in range(0, len(arguments) - 2, 2):
            if arguments[i] == "-o":
                options.append(arguments[i + 1])
            elif arguments[i] == "-i":
                identity_file = arguments[i + 1]
                break

        head_user_and_ip = arguments[-1]

        return SSHConfig(options, identity_file, head_user_and_ip, ssh_command_str)


# ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o 'ProxyCommand=websocat asyncstdio: ws://127.0.0.1:7465/net-api/v1/net/945ba8d26bfe4294a22d400e2b5b628b/tcp/192.168.0.3/22 --binary -H=Authorization:'"'"'Bearer 34722ec7c8264a94aa888b53347b212e'"'"'' -i /tmp/ray_on_golem/ray_on_golem_rsa_2b6976a4b5 root@192.168.0.3
# def parse_ssh_command(ssh_command_str):
#     """parse arguments needed for an ssh connection from an example ssh command

#     Args:
#         ssh_command_str (str): an example ssh command to connect to a remote node

#     Returns:
#         SSHConfig: object
#     """

#     invocation_args = ssh_command_str[3:].strip()
#     arguments = shlex.split(invocation_args)
#     options = []

#     for i in range(1, 6, 2):
#         options.append(arguments[i])

#     identity_file = arguments[7]

#     head_user_and_ip = arguments[8]

#     ssh_config = SSHConfig(options, identity_file, head_user_and_ip, ssh_command_str)

#     return ssh_config


def scp_bulk_transfer(
    mode, source_files, target_dir, ssh_config, delete_after_source_transfer=True
):
    """
    Transfer multiple files to or from the head node using SCP.

    :param mode: 'put' to upload or 'get' to download.
    :param source_files: a list of paths to source files.
    :param target_dir: the target directory path where files will be transferred.
    :param ssh_config: an SSHConfig object.
    :param delete_after_source_transfer: Delete source files after 'put', default is True.

    :raises ValueError: for invalid transfer mode.
    :raises subprocess.CalledProcessError: for errors during SCP command execution.
    :raises FileNotFoundError: if a source file to be transferred is not found.
    """
    if mode not in ["put", "get"]:
        raise ValueError("Invalid mode. Choose 'put' or 'get'.")

    scp_command = ["scp"] + ssh_config.ssh_arguments_list
    if mode == "put":
        for source in source_files:
            scp_command.extend([source, f"{ssh_config.head_user_and_ip}:{target_dir}"])
    elif mode == "get":
        # Append all remote file paths first
        for source in source_files:
            scp_command.append(f"{ssh_config.head_user_and_ip}:{source}")
        # Append the local directory target at the end
        scp_command.append(target_dir)

    try:
        process_result = subprocess.run(
            scp_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, check=True
        )
        if process_result.stdout:
            logging.debug(process_result.stdout.decode("utf-8"))

        if mode == "put" and delete_after_source_transfer:
            for source_file in source_files:
                os.remove(source_file)
                logging.debug(f"Successfully moved source file {source_file} to target")

    except subprocess.CalledProcessError as e:
        logging.error(f"SCP command {scp_command} failed: {e.stderr.decode('utf-8')}")
        raise
    except FileNotFoundError as e:
        logging.error(f"File not found error: {e}")
        raise


# included for thoroughness, but project needs only scp_bulk_transfer
def scp_transfer(mode, localfile, remotefile, ssh_config, delete_after_put=True):
    """
    Put or get files from the head node

    Args:
        localfile (stringable): path to the local file
        remotefile (stringable): path to the remote file
        ssh_config (SSHConfig): an SSHConfig object
        delete_after_put (bool): Optional, defaults to True

    note: removes local files put to the head node
    """

    if mode == "put":
        scp_command = (
            ["scp"]
            + ssh_config.ssh_arguments_list
            + [localfile, f"{ssh_config.head_user_and_ip}:{remotefile}"]
        )
    elif mode == "get":
        scp_command = (
            ["scp"]
            + ssh_config.ssh_arguments_list
            + [f"{ssh_config.head_user_and_ip}:{remotefile}", localfile]
        )
    else:
        raise ValueError("invalid mode. choose 'put' or 'get'.")

    try:
        process_result = subprocess.run(
            scp_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, check=True
        )
        if len(process_result.stdout) > 0:
            logging.debug(process_result.stdout.decode("utf-8"))
        if mode == "put" and delete_after_put:
            # remove the local file after successful upload
            os.remove(localfile)
            logging.debug(f"successfully moved local file {localfile} to remote head")
    except subprocess.CalledProcessError as e:
        logging.error(f"scp command {scp_command} failed: {e}")
        raise
    except FileNotFoundError as e:
        logging.error(f"file not found error: {e}")
        raise


# broken
# def rsync(remotepath, localpath, ssh_config):
#     # broken
#     rsync_command = (
#         ["rsync", "-avz", "-e", "ssh"]
#         + [" ".join(ssh_config.ssh_arguments_list)]
#         + [localpath]
#         + [f"{ssh_config.head_user_and_ip}:{remotepath}"]
#     )

#     try:
#         subprocess.run(rsync_command, check=True)
#     except subprocess.CalledProcessError as e:
#         logging.error(f"rsync command failed: {e}")
#         raise
#     except FileNotFoundError as e:
#         logging.error(f"File not found error: {e}")
#         raise
