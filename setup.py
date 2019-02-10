import setuptools

setuptools.setup(
    name="SolonBot",
    version="0.0.4",
    description="Discord bot for general server and community management. Uses Solon library.",
    author="Falsely True Bots",
    author_email="FalselyTrueBots@users.noreply.github.com",
    url="https://github.com/FalselyTrueBots",
    packages=["solonbot"],
    install_requires=[
        "solon @ git+ssh://git@github.com/FalselyTrueBots/solon@3bf72ace48fb2b4bdac8ab7ee875011145df0a57#egg=solon-0.0.3"
    ]
)
