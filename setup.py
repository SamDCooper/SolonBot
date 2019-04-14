import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.1.18",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@1f83507936c322f6397cbdba1e5e1bbdf83a086c#egg=solon-0.0.5"
    ]
)
