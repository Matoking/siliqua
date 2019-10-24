import sys

import click

from siliqua import __version__
from siliqua.config import (create_config_files, get_config,
                              get_default_config_path)
from siliqua.logger import set_verbosity_level
from siliqua.plugins import (get_network_plugins, get_ui_plugins,
                               get_work_plugins)
from siliqua.server import WalletServer
from toml.decoder import TomlDecodeError


def config_callback(ctx, param, value):
    """
    Load the configuration file and add it into the context

    :return: Config instance
    :rtype: siliqua.config.Config
    """
    ctx.ensure_object(dict)

    if "config" in ctx.obj:
        # If the Config instance already exists, don't recreate it
        return None

    try:
        config = get_config(value)
    except TomlDecodeError:
        raise click.BadParameter("configuration file is invalid")

    ctx.obj["config"] = config

    return config


def plugin_callback(ctx, param, value):
    """
    Load correct plugin and add it into the context
    """
    config = ctx.obj["config"]

    # Selection through CLI
    if value:
        ctx.ensure_object(dict)
        ctx.obj[param.name] = value
        return value

    # Selection through configuration file
    value = config.get("main.default_{}_plugin".format(param.name), None)

    if value:
        return value

    raise click.BadParameter("{} plugin not set".format(param.name))


def ui_callback(ctx, param, value):
    """
    Load correct UI plugin and add it into the context
    """
    plugin_name = plugin_callback(ctx, param, value)

    plugin_cls = get_ui_plugins()[plugin_name]
    plugin = plugin_cls(config=ctx.obj["config"])
    ctx.obj[param.name] = plugin

    return plugin


def work_callback(ctx, param, value):
    """
    Load correct work plugin and add it into the context
    """
    plugin_name = plugin_callback(ctx, param, value)

    plugin_cls = get_work_plugins()[plugin_name]
    plugin = plugin_cls(config=ctx.obj["config"])
    ctx.obj[param.name] = plugin

    return plugin


def network_callback(ctx, param, value):
    """
    Load correct network plugin and add it into the context
    """
    plugin_name = plugin_callback(ctx, param, value)

    plugin_cls = get_network_plugins()[plugin_name]
    plugin = plugin_cls(config=ctx.obj["config"])
    ctx.obj[param.name] = plugin

    return plugin


def version_callback(ctx, param, value):
    """
    Print version information and abort execution
    """
    if not value or ctx.resilient_parsing:
        return

    click.echo("version {}".format(__version__))
    click.echo("\nInstalled plugins:")

    plugins = {
        **get_ui_plugins(), **get_work_plugins(), **get_network_plugins()
    }
    plugin_names = sorted(list(plugins.keys()))
    click.echo(", ".join(plugin_names))

    sys.exit(0)


@click.option(
    "--version", is_flag=True, is_eager=True, expose_value=False,
    callback=version_callback,
    help="Print version information"
)
@click.command(context_settings={
    "ignore_unknown_options": True,
    "allow_extra_args": True
}, add_help_option=False)
@click.option(
    "--config", type=click.Path(exists=True, file_okay=True),
    callback=config_callback, is_eager=True,
    help=(
        "Siliqua configuration file to use. Defaults to "
        "{}".format(get_default_config_path())
    )
)
@click.option(
    "--wallet", type=click.Path(exists=True, file_okay=True),
    help="Wallet file to load. May be mandatory depending on the GUI plugin.")
@click.option(
    "-v", "--verbose", default=0, count=True,
    help=(
        "Set logging level. By default only ERROR messages are logged.\n\n"
        "-v = WARNING\n-vv = INFO\n-vvv = DEBUG"
    )
)
@click.option(
    "--ui", required=False,
    type=click.Choice(get_ui_plugins().keys()),
    callback=ui_callback,
    help=(
        "User interface plugin to use"
    )
)
@click.option(
    "--work", required=False,
    type=click.Choice(get_work_plugins().keys()),
    callback=work_callback,
    help="PoW plugin to use")
@click.option(
    "--network", required=False,
    type=click.Choice(get_network_plugins().keys()),
    callback=network_callback,
    help="Network plugin to use")
@click.pass_context
def cli_init(ctx, *args, **kwargs):
    # Run the argument parser once to select the GUI and set logging...
    create_config_files()

    set_verbosity_level(kwargs.get("verbose", 0))

    return ctx.obj


def main(args=None):
    """
    The main CLI entry point.

    The CLI consists of two Click commands forming a two-stage CLI:

    * The first stage "cli_init" discovers the plugins selected by the user.
      This allows us to populate the next Click command
      with plugin-specific options for the second stage.
      This first stage should NEVER fail.

    * The second run "cli" to provide all the CLI options and start the actual
      execution of the application.
    """
    # Ensure configuration exists
    create_config_files()

    # Run 'cli_init' to determine which plugins are in use
    try:
        result = cli_init(args=args, standalone_mode=False)
    except click.ClickException as e:
        # TODO: If '--help' was invoked at this stage, print it instead
        e.show()
        return

    config = result["config"]
    ui_plugin = result["ui"]
    work_plugin = result["work"]
    network_plugin = result["network"]

    # Start the second run by pre-populating the click.Context instance
    # with the loaded plugins.
    # This allows us to override configurations options in the Config instance
    # with those provided as CLI parameters.
    obj_defaults = {
        "ui": ui_plugin,
        "work": work_plugin,
        "network": network_plugin,
        "config": config,
    }

    # Does the GUI plugin's CLI interface consist of multiple subcommands?
    try:
        cli = click.Group(
            params=(
                cli_init.params
                + work_plugin.get_cli_params()
                + network_plugin.get_cli_params()
            ),
            context_settings={"obj": obj_defaults}
        )
        for cmd in ui_plugin.get_cli().commands:
            cli.add_command(cmd)
    except AttributeError:
        cli = click.Command(
            name="run",
            params=cli_init.params + ui_plugin.get_cli().params,
            callback=(
                lambda *args, **kwargs:
                    ui_plugin.run_from_cli(ui_plugin, *args, **kwargs)
            )
        )

    cli(args=args)


if __name__ == "__main__":
    main()
