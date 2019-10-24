import pytest

import os
import json


@pytest.fixture(scope="function")
def stdio(cli, config, is_encrypted_test):
    if not config.get("network.nano_node.rpc_url", None):
        # Set the 'rpc_url' field even if we're not connecting to network
        # to ensure configuration is complete
        config.set("network.nano_node.rpc_url", "http://127.0.0.1:9076")
        config.save()

    def run_stdio(args, env=None, success=True, raw=False):
        if not env:
            env = {}

        if is_encrypted_test:
            env["PASSPHRASE"] = "password"

        environ_copy = os.environ.copy()
        try:
            os.environ.update(env)
            result = cli(
                args=["--config", config.path, "-vvv", "--ui", "stdio"] + args
            )
            output = result.out
        finally:
            os.environ.clear()
            os.environ.update(environ_copy)

        if raw:
            return result.out + result.err

        # Try to remove prompt output before the actual JSON result
        if "{" in output:
            output = output[output.find("{"):]

        output = json.loads(output)
        if success:
            assert output["status"] == "success", "Expected success, got {} instead".format(output)
        else:
            assert output["status"] == "error", "Expected failure, got {} instead".format(output)

        return output

    return run_stdio
