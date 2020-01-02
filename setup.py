from setuptools import find_packages, setup

__version__ = "0.1.0"

setup(
    name="shamiko",
    version=__version__,
    description="Shamiko ga waruindayo",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Yuki Igarashi",
    author_email="me@bonprosoft.com",
    url="https://github.com/bonprosoft/shamiko",
    license="MIT License",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
    ],
    package_data={"shamiko": ["py.typed", "templates/*.template"]},
    install_requires=["psutil>=5.6.7,<6", "Jinja2>=2.10.3,<3"],
    entry_points={"console_scripts": ["shamiko = shamiko.cli:cli"]},
    zip_safe=False,
)
