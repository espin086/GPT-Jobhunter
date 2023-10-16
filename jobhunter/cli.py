import click
import os
from streamlit.web import cli as stcli


@click.command()
def main():
    # Get the directory where cli.py is located
    cli_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path to main.py
    main_path = os.path.join(cli_dir, "main.py")

    click.echo("Running the Streamlit app...")
    stcli.main(["run", main_path])


if __name__ == "__main__":
    main()
