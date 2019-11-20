import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.1.27",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@782f7fc407b0e8f626cb1bfd50c4caca75cfe8bc#egg=solon-0.0.8"
    ]
)
