import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.1.21",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@38821a416398a8d6a278974ddf2bf76efeacf667#egg=solon-0.0.6"
    ]
)
