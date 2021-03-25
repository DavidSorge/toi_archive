from setuptools import setup

setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name='toi_archive',
    url='https://github.com/DavidSorge/toi_archive',
    author='David Sorge',
    author_email='david.c.sorge@gmail.com',
    # Needed to actually package something
    packages=['toi_archive'],
    # Needed for dependencies
    install_requires=['regex', 'Ipython', 'pandas'],
    # *strongly* suggested for sharing
    version='0.1',
    # The license can be anything you like
    license='MIT',
    description='An example of a python package from pre-existing code',
    # We will also need a readme eventually (there will be a warning)
    long_description=open('README.txt').read(),
)