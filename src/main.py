import yaml

def main():
    # temporary file
    with open("config.yml", "r") as f:
        config = yaml.safe_load(f)
        print(config)

if __name__ == "__main__":
    main()