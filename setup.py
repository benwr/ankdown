from os import path

from codecs import open as codec_open
from setuptools import setup, find_packages

HERE = path.abspath(path.dirname(__file__))

with codec_open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setup(
    name="ankdown",
    version="0.5.2",
    description="A utility for converting Markdown into Anki cards",
    long_description=LONG_DESCRIPTION,
    url="https://github.com/benwr/ankdown",

    author="Ben Weinstein-Raun",
    author_email="b@w-r.me",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="anki spaced-repetition markdown math latex",
    packages=find_packages(),
    install_requires=['genanki>=0.6.3', 'misaka>=2.1.0', 'docopt>=0.6.2'],
    entry_points={
        "console_scripts": [
            "ankdown=ankdown.ankdown:main"
        ]
    }
)
