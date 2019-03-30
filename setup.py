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
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@2acc1bb134eef1e50d7625a1a4bf56a45e219964#egg=solon-0.0.4"
    ]
)
