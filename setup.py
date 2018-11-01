"""Setup for dado."""


# [ Imports:Third Party ]
import setuptools  # type: ignore


# [ Main ]
setuptools.setup(
    name='dado',
    version='0.1.4',
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
    packages=setuptools.find_packages(),
    package_data={
        'dado': ['py.typed'],
    },
    install_requires=[],
    extras_require={
        'test': [
            'bandit',  # no-import: standalone bin
            'better_exceptions',
            'blessed',
            'click',
            'coverage',
            'flake8-assertive',  # no-import: plugin
            'flake8-author',  # no-import: plugin
            'flake8-blind-except',  # no-import: plugin
            'flake8-bugbear',  # no-import: plugin
            'flake8-builtins-unleashed',  # no-import: plugin
            'flake8-commas',  # no-import: plugin
            'flake8-comprehensions',  # no-import: plugin
            'flake8-copyright',  # no-import: plugin
            'flake8-debugger',  # no-import: plugin
            'flake8-docstrings',  # no-import: plugin
            'flake8-double-quotes',  # no-import: plugin
            'flake8-expandtab',  # no-import: plugin
            'flake8-imports',  # no-import: plugin
            'flake8-logging-format',  # no-import: plugin
            'flake8-mutable',  # no-import: plugin
            'flake8-pep257',  # no-import: plugin
            'flake8-self',  # no-import: plugin
            'flake8-single-quotes',  # no-import: plugin
            'flake8-super-call',  # no-import: plugin
            'flake8-tidy-imports',  # no-import: plugin
            'flake8-todo',  # no-import: plugin
            'flake8',  # no-import: standalone bin
            'mypy',  # no-import: standalone bin
            'pylint',  # no-import: standalone bin
            'pipe',
            'vulture',  # no-import: standalone bin
        ],
    },
)
