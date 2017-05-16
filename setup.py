
import re

from setuptools import setup

def parse_requirements(file_name):
    requirements = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        if re.match(r'\s*-e\s+', line):
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1', line))
        elif re.match(r'\s*-f\s+', line):
            pass
        else:
            requirements.append(line)

    return requirements


setup(
    name='BigSea Load Balancer',
    version='0.1.0',
    description='Python daemon to manage a specific subset off hosts',
    url='',
    author='Iury Gregory Melo Ferreira',
    author_email='iurygregory@gmail.com',
    license='Apache 2.0',
    install_requires=parse_requirements('requirements.txt'),
)
