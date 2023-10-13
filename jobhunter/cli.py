import click
from streamlit.web import cli as stcli

@click.command()
def main():
    click.echo("Running the Streamlit app...")
    stcli.main(["run", "main.py"])

if __name__ == '__main__':
    main()
