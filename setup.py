import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.1.28",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@9acafe3552a7e997dbcb4729c7d214b2d758ec14#egg=solon-0.0.10"
    ]
)
