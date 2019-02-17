import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.1.10",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@4f0802cdf60f76f2befe48f26b87ea9a30ee1d17#egg=solon-0.0.3"
    ]
)
