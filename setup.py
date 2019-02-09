import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.0.3",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@7900c0eb7d36673e232639c934c72b43bd88fce7#egg=solon-0.0.3"
    ]
)
