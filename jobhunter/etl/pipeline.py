from extract import extract
from transform import transform
from load import load
from delete_local import run as delete_local

def run():
    extract()
    transform()
    load()
    delete_local()

if __name__ == "__main__":
    run()




