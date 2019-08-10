import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.1.23",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@de3c3dc4328f3a6ce89f87826ae8a3c4b7afa301#egg=solon-0.0.7"
    ]
)
