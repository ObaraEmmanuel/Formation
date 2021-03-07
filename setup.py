from setuptools import find_packages, setup
from os import path
import codecs


def read(rel_path):
    here = path.abspath(path.dirname(__file__))
    with codecs.open(path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

requirements = open("requirements.txt").readline()

COMMANDS = [
    'formation-studio = studio.main:main',
]


setup(
    name='formation-studio',
    packages=find_packages("src"),
    package_dir={"": "src",},
    version=get_version('src/formation/__init__.py'),
    license='MIT',
    description='Simplify GUI development in python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Hoverset',
    author_email='emmanuelobarany@gmail.com',
    url='https://github.com/ObaraEmmanuel/Formation',
    keywords=['formation', 'gui', 'graphical-user-interface', 'drag drop', 'tkinter', 'hoverset', 'python'],
    install_requires=requirements,
    package_data={
        'hoverset.data': ['image.*'],
        'hoverset.ui': ['themes/*'],
        'studio': ['resources/*/*']
    },
    entry_points={"gui_scripts": COMMANDS},
    classifiers=[
        'Development Status :: 4 - Beta',
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable"
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        'Topic :: Software Development :: User Interfaces',
        'Operating System :: OS Independent'
    ],
)
