from setuptools import setup

setup(
    name="shamiko",
    version="0.0.1",
    description="Shamiko ga waruindayo",
    long_description="",
    author="Yuki Igarashi",
    author_email="me@bonprosoft.com",
    url="https://github.com/bonprosoft/shamiko",
    license="MIT License",
    packages=["shamiko", "shamiko.gdb", "shamiko.simple_rpc"],
    package_data={
        "shamiko": [
            "templates/*.template",
        ],
    },
    install_requires=[
        "psutil>=5.6.7,<6",
    ],
    entry_points={
        "console_scripts": [
            "shamiko = shamiko.cli:cli",
        ],
    },
)
