import os
import pytest

# Sample SSH config for testing
FAKE_SSH_CONFIG = """
    ### default for all ##
    Host *
         ForwardAgent no
         ForwardX11 no
         ForwardX11Trusted yes
         User nixcraft
         Port 22
         Protocol 2
         ServerAliveInterval 60
         ServerAliveCountMax 30
         LocalForward 3128 127.0.0.1:3128
         LocalForward 3129 127.0.0.1:3128

    ## override as per host ##
    Host server1
         HostName server1.cyberciti.biz
         User nixcraft
         Port 4242
         IdentityFile /nfs/shared/users/nixcraft/keys/server1/id_rsa
         IdentityFile /tmp/x.rsa

    ## Home nas server ##
    Host nas01
         HostName 192.168.1.100
         User root
         IdentityFile ~/.ssh/nas01.key

    ## Login AWS Cloud ##
    Host aws.apache
         HostName 1.2.3.4
         User wwwdata
         IdentityFile ~/.ssh/aws.apache.key

    ## Login to internal lan server via gateway ##
    Host uk.gw.lan uk.lan
         HostName 192.168.0.251
         User nixcraft
         ProxyCommand  ssh nixcraft@gateway.uk.cyberciti.biz nc %h %p 2> /dev/null

    ## Our Us Proxy Server ##
    Host proxyus
        HostName vps1.cyberciti.biz
        User breakfree
        IdentityFile ~/.ssh/vps1.cyberciti.biz.key
        LocalForward 3128 127.0.0.1:3128
"""

SIMPLE_SSH_CONFIG = """Host *
    IdentitiesOnly yes

Host netscaler
    hostname 1.1.1.1
    port 3367

"""


@pytest.fixture
def ssh_config_file(tmp_path):
    """Create a temporary SSH config file for testing."""
    config_file = tmp_path / "ssh_config"
    config_file.write_text(FAKE_SSH_CONFIG)
    return str(config_file)


@pytest.fixture
def simple_ssh_config_file(tmp_path):
    """Create a simple temporary SSH config file for testing."""
    config_file = tmp_path / "ssh_config"
    config_file.write_text(SIMPLE_SSH_CONFIG)
    return str(config_file)


@pytest.fixture
def storm_instance(simple_ssh_config_file):
    """Create a Storm instance with a simple config."""
    from storm import Storm
    return Storm(simple_ssh_config_file)


@pytest.fixture(autouse=True)
def set_test_mode():
    """Set TESTMODE environment variable for all tests."""
    os.environ["TESTMODE"] = "1"
    yield
    if "TESTMODE" in os.environ:
        del os.environ["TESTMODE"]
