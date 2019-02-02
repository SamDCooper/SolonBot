import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.0.1",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=["solon @ git+ssh://git@github.com/FalselyTrueBots/solon@ff88adea69f09dcb26ab72d4870f4939213ec7f8#egg=solon-0.0.1"]
)
