import os
import re
from pathlib import Path

PORT_MAP = {
    '22357': '8083',  # LINE
    '22358': '8084',  # App
    '22359': '8085'   # Code
}

def replace_ports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old_port, new_port in PORT_MAP.items():
        content = re.sub(rf'(?<=:)\s*{old_port}\b', f' {new_port}', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    root_dir = Path('.')
    for file in root_dir.rglob('*'):
        if file.suffix in ['.yml', '.yaml', '.js'] and 'node_modules' not in str(file):
            replace_ports(file)

if __name__ == '__main__':
    main() 