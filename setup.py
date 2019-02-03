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
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@3d4aa6e90ad13aab637761c8e321ebf365a300a6#egg=solon-0.0.2"
    ]
)
