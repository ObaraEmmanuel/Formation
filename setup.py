from setuptools import setup

import formation

requirements = ['lxml', 'Pillow', 'pyscreenshot', 'pywin32 ; sys_platform=="win32"']

setup(
    name='formation-studio',
    packages=['hoverset', 'hoverset.data', 'hoverset.platform', 'hoverset.ui', 'hoverset.util',
              'formation',
              'studio', 'studio.feature', 'studio.lib', 'studio.parsers', 'studio.ui'],
    version=formation.__version__,
    license='MIT',
    description='Simplify GUI development in python',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        'Topic :: Software Development :: User Interfaces',
        'Operating System :: OS Independent'
    ],
)
