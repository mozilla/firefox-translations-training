import yaml
import sys

base_dir=sys.argv[1]
config=sys.argv[2]

yml = yaml.load(open(config))

reports_path=f"{base_dir}/reports/{yml['experiment']['src']}-{yml['experiment']['trg']}/{yml['experiment']['name']}"

sys.stdout.write(reports_path)