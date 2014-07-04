from setuptools import setup

from specter import version


def listify(filename):
    return filter(None, open(filename, 'r').read().strip('\n').split('\n'))

setup(
    name="specter",
    version=version.VERSION,
    url='http://github.com/praekelt/specter',
    license='MIT',
    description="A generic server agent",
    long_description=open('README.rst', 'r').read(),
    author='Colin Alston',
    author_email='colin.alston@praekelt.com',
    packages=[
        "specter",
        "twisted.plugins",
    ],
    package_data={
        'twisted.plugins': ['twisted/plugins/specter_plugin.py']
    },
    include_package_data=True,
    install_requires=listify('requirements.txt'),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
    ],
)
