from setuptools import setup, find_packages

__version__ = '1.0.0b'

LONG_DESCRIPTION = open("README.md", "r", encoding="utf-8").read()

tests_require = [
    'pytest',
    'pytest-mock',
]

setup(
    name="data-collector",
    version=__version__,
    author="Duk Kyu Lim",
    author_email="deokyu@vivans.net",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    description='Data Collector',
    url="",
    license="MIT",
    keywords=[],
    install_requires=[
        'flask',
        'PyYaml',
        'apscheduler',
        'celery',
        'requests',
        'redis'
    ],
    tests_require=tests_require,
    packages=find_packages(
        exclude=['tests', 'tests.*']),
    package_data={},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        'console_scripts': [
            'data-collector=data_collector.__main__:main',
        ],
    },
    zip_safe=False,
)
