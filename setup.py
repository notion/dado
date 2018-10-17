"""Setup for dado."""


# [ Imports ]
# [ -Python ]
from setuptools import setup, find_packages


# [ Main ]
setup(
    name='dado',
    version='0.1.3',
    description='Dado: Data Driven Test Decorator.',
    url='https://github.com/notion/dado',
    author='toejough',
    author_email='toejough@gmail.com',
    classifiers=[
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 3 - Alpha',

            # Indicate who your project is intended for
            'Intended Audience :: Developers',

            # Pick your license as you wish (should match "license" above)
            'License :: OSI Approved :: Apache Software License',

            # Specify the Python versions you support here. In particular, ensure
            # that you indicate whether you support Python 2, Python 3 or both.
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.7',
    ],
    keywords="data-driven test decorator",
    py_modules=['dado'],
)
