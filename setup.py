import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.0.1",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=["solon @ git+ssh://git@github.com/FalselyTrueBots/solon@b1095c8bfefe2ca1294e52827bfa5d5d6443d4b2#egg=solon-0.0.1"]
)
