import setuptools

with open("README.md", "r") as f:
    readme = f.read()

setuptools.setup(
    name="pyacaia_async",
    version="0.0.11b5",
    description="An async implementation of PyAcaia",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/zweckj/pyacaia_async",
    author="Josef Zweck",
    author_email="24647999+zweckj@users.noreply.github.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    packages=setuptools.find_packages(),
    install_requires=["bleak>=0.20.2"],
    package_data={
        "pyacaia_async": ["py.typed"],
    },
)
