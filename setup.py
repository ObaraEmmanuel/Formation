from setuptools import setup
import formation
import sys

requirements = ['lxml', 'Pillow>=6.0.0', 'pyscreenshot']
if sys.platform == 'win32':
    requirements.append('pywin32')

setup(
    name='formation',
    packages=['hoverset', 'hoverset.data', 'hoverset.platform', 'hoverset.ui', 'hoverset.util',
              'formation',
              'studio', 'studio.feature', 'studio.lib', 'studio.parsers', 'studio.ui'],
    version=formation.__version__,
    license='MIT',
    description='Simplify GUI development in python',
    author='Hoverset',
    author_email='emmanuelobarany@gmail.com',
    url='https://github.com/ObaraEmmanuel/Formation',
    keywords=['formation', 'gui', 'graphical-user-interface', 'drag drop', 'tkinter', 'hoverset'],
    install_requires=requirements,
    package_data={
        'hoverset.data': ['image.*'],
        'hoverset.ui': ['themes/*'],
        'studio': ['resources/*/*']
    },
    entry_points={
        'gui_scripts': [
            'formation-studio = studio.main:main',
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable"
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        'Topic :: Software Development :: User Interfaces',
        'Operating System :: OS Independent'
    ],
)
