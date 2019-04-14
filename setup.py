import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.1.19",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@fe5e5b8b6d90dde1b255fa8cd3fdc40d3c41f6b3#egg=solon-0.0.5"
    ]
)
