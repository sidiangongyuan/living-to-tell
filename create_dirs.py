#!/usr/bin/env python3
import os
import pathlib

# Create all required directories
directories = [
    r'D:\python_proj\writer\src\writer\app',
    r'D:\python_proj\writer\src\writer\storage\repositories',
    r'D:\python_proj\writer\src\writer\ui',
    r'D:\python_proj\writer\tests\storage'
]

print("Creating directories...")
for dir_path in directories:
    pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
    print(f'✓ Created: {dir_path}')

print('\n' + '='*60)
print('Directory Tree for D:\\python_proj\\writer\\src')
print('='*60)

def print_tree(directory, prefix=""):
    """Print directory tree structure"""
    try:
        entries = sorted(os.listdir(directory))
        dirs = [e for e in entries if os.path.isdir(os.path.join(directory, e))]
        
        for i, dir_name in enumerate(dirs):
            is_last = (i == len(dirs) - 1)
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{dir_name}/")
            
            next_prefix = prefix + ("    " if is_last else "│   ")
            next_path = os.path.join(directory, dir_name)
            print_tree(next_path, next_prefix)
    except Exception as e:
        pass

if os.path.exists(r'D:\python_proj\writer\src'):
    print("src/")
    print_tree(r'D:\python_proj\writer\src', "")

print('\n' + '='*60)
print('Directory Tree for D:\\python_proj\\writer\\tests')
print('='*60)

if os.path.exists(r'D:\python_proj\writer\tests'):
    print("tests/")
    print_tree(r'D:\python_proj\writer\tests', "")
