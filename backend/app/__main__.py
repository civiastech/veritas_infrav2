import argparse
from app.seed.runner import run_all

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["core", "demo", "test"], default="demo")
args = parser.parse_args()

run_all(mode=args.mode)